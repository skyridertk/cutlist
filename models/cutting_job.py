import base64
import tempfile
import os
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use Agg backend to avoid GUI
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
# Import the EnhancedCuttingStockOptimizer from paste5
from odoo.addons.cutlist.models.paste5 import Panel, StockSheet, OptimizerOptions, EnhancedCuttingStockOptimizer
        

class CuttingJob(models.Model):
    _name = 'cutting.job'
    _description = 'Cutting Stock Optimization Job'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char('Name', required=True, index=True, tracking=True, 
                     default=lambda self: _('New Cutting Job'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('optimized', 'Optimized'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    stock_sheet_id = fields.Many2one('cutting.stock.sheet', string='Stock Sheet', required=True, 
                                    tracking=True, states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]})
    options_id = fields.Many2one('cutting.optimizer.options', string='Optimization Options', required=True, 
                               tracking=True, states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]})
    
    line_ids = fields.One2many('cutting.job.line', 'cutting_job_id', string='Panels', 
                             states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]})
    
    # Results
    optimization_date = fields.Datetime('Optimization Date', readonly=True, copy=False)
    sheet_usage_ratio = fields.Float('Sheet Usage Ratio', readonly=True, help="Percentage of stock sheet area used by panels", copy=False)
    waste_area = fields.Float('Waste Area', readonly=True, help="Area wasted in the cutting pattern", copy=False)
    total_panels = fields.Integer('Total Panels Placed', readonly=True, copy=False)
    optimization_time = fields.Float('Optimization Time (s)', readonly=True, help="Time taken to run the optimization in seconds", copy=False)
    
    # PDF Report
    pattern_pdf = fields.Binary('Cutting Pattern PDF', readonly=True, attachment=True, copy=False)
    pattern_pdf_filename = fields.Char('PDF Filename', copy=False)
    
    notes = fields.Text('Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New Cutting Job')) == _('New Cutting Job'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cutting.job') or _('New Cutting Job')
        return super(CuttingJob, self).create(vals_list)
    
    def action_ready(self):
        for job in self:
            if not job.line_ids:
                raise UserError(_("You must add at least one panel to the cutting job."))
            job.write({'state': 'ready'})
        return True
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True
    
    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True
    
    def action_done(self):
        self.write({'state': 'done'})
        return True
        
    def _run_maxrects_optimizer(self, panels, stock_sheet, options):
        """
        Run the enhanced MaxRects optimization algorithm.
        
        Returns a dictionary with:
        - usage_ratio: ratio of used area to total area
        - waste_area: area wasted
        - total_panels: number of panels placed
        - pdf_data: base64-encoded PDF data
        """
       
        # Debug the input data
        print(f"Input data: Sheet {stock_sheet['length']}x{stock_sheet['width']}")
        total_panel_count = sum(p['quantity'] for p in panels)
        print(f"Panels to place: {total_panel_count}")
        
        # Convert input data to the optimizer's expected format
        optimizer_panels = []
        
        # First approach: Create one panel object per instance
        for panel_data in panels:
            panel_obj = Panel(
                length=float(panel_data['length']),  # Ensure these are floats
                width=float(panel_data['width']),
                quantity=int(panel_data['quantity']),  # Pass actual quantity
                label=panel_data['label'],
                material=panel_data['material'],
                grain_direction=panel_data['grain_direction']
            )
            optimizer_panels.append(panel_obj)
        
        optimizer_stock_sheet = StockSheet(
            length=float(stock_sheet['length']),  # Ensure these are floats
            width=float(stock_sheet['width']),
            quantity=int(stock_sheet['quantity']),
            material=stock_sheet['material'],
            label=stock_sheet['label'],
            grain_direction=stock_sheet['grain_direction']
        )
        
        optimizer_options = OptimizerOptions(
            kerf_thickness=float(options['kerf_thickness']),  # Ensure this is a float
            labels_on_panels=bool(options['labels_on_panels']),
            use_single_sheet=bool(options['use_single_sheet']),
            consider_material=bool(options['consider_material']),
            edge_banding=bool(options['edge_banding']),
            consider_grain=bool(options['consider_grain'])
        )
        
        # Create and run the enhanced optimizer
        print("Creating optimizer with converted data...")
        optimizer = EnhancedCuttingStockOptimizer(optimizer_panels, optimizer_stock_sheet, optimizer_options)
        
        print("Running optimization...")
        best_pattern = optimizer.optimize()
        
        # Debug the results
        sheet_area = optimizer_stock_sheet.area()
        waste_area = best_pattern.waste_area
        used_area = sheet_area - waste_area
        usage_ratio = used_area / sheet_area
        
        print(f"Optimization results:")
        print(f"Sheet area: {sheet_area:.2f}")
        print(f"Used area: {used_area:.2f}")
        print(f"Waste area: {waste_area:.2f}")
        print(f"Usage ratio: {usage_ratio:.4f} ({usage_ratio * 100:.2f}%)")
        print(f"Panels placed: {len(best_pattern.placed_panels)}")
        
        # Generate the PDF visualization
        pdf_data = self._generate_cutting_pattern_pdf_enhanced(best_pattern, optimizer_stock_sheet, optimizer_options)
        
        # Return clean, precise results
        return {
            'usage_ratio': usage_ratio,  # This is a proportion (0-1), not a percentage
            'waste_area': float(waste_area),
            'total_panels': len(best_pattern.placed_panels),
            'pdf_data': pdf_data,
        }

    def action_run_optimization(self):
        """Modified optimization action with better error handling and debugging."""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_("You must add at least one panel to the cutting job."))
        
        # Run optimization
        start_time = datetime.now()
        
        # Convert panels and stock sheet to the format needed by the optimizer
        panels = []
        for line in self.line_ids:
            panels.append({
                'id': line.id,
                'length': line.panel_id.length,
                'width': line.panel_id.width,
                'quantity': line.quantity,
                'label': line.panel_id.name,
                'material': line.panel_id.material_id.id if line.panel_id.material_id else 'default',
                'grain_direction': line.panel_id.grain_direction,
            })
        
        stock_sheet = {
            'length': self.stock_sheet_id.length,
            'width': self.stock_sheet_id.width,
            'quantity': self.stock_sheet_id.available_quantity,
            'material': self.stock_sheet_id.material_id.id if self.stock_sheet_id.material_id else 'default',
            'label': self.stock_sheet_id.name,
            'grain_direction': self.stock_sheet_id.grain_direction,
        }
        
        options = {
            'kerf_thickness': self.options_id.kerf_thickness,
            'labels_on_panels': self.options_id.labels_on_panels,
            'use_single_sheet': self.options_id.use_single_sheet,
            'consider_material': self.options_id.consider_material,
            'edge_banding': self.options_id.edge_banding,
            'consider_grain': self.options_id.consider_grain,
        }
        
        # For debugging
        print(f"Optimization job started for sheet {stock_sheet['length']}x{stock_sheet['width']}")
        print(f"Panels to optimize: {panels}")
        
        try:
            # Call optimizer function with enhanced algorithm
            result = self._run_maxrects_optimizer(panels, stock_sheet, options)
            
            end_time = datetime.now()
            optimization_time = (end_time - start_time).total_seconds()
            
            # Debug the result before writing
            print(f"Raw optimization result: {result}")
            print(f"Usage ratio: {result.get('usage_ratio', 0)}")
            print(f"Usage percentage: {result.get('usage_ratio', 0) * 100:.2f}%")
            
            # Update job with results - ensure all values are of correct type
            self.write({
                'state': 'optimized',
                'optimization_date': fields.Datetime.now(),
                'sheet_usage_ratio': float(result.get('usage_ratio', 0) * 100),  # Convert to percentage
                'waste_area': float(result.get('waste_area', 0)),
                'total_panels': int(result.get('total_panels', 0)),
                'optimization_time': float(optimization_time),
                'pattern_pdf': result.get('pdf_data'),
                'pattern_pdf_filename': f"cutting_pattern_{self.name.replace(' ', '_')}.pdf",
            })
            
            # Verify values after write
            self.env.cr.commit()  # Commit the transaction to avoid losing debug output
            print(f"Values after write: ratio={self.sheet_usage_ratio}%, waste={self.waste_area}, panels={self.total_panels}")
            
            return True
            
        except Exception as e:
            # Log the error but don't raise it to avoid transaction rollback
            import traceback
            print(f"Error in optimization: {e}")
            print(traceback.format_exc())
            raise UserError(_(f"Optimization failed: {e}"))
            
    def _generate_cutting_pattern_pdf_enhanced(self, pattern, stock_sheet, options):
        """Generate a PDF visualization of the cutting pattern using the enhanced optimizer's output."""
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        
        try:
            with PdfPages(temp_path) as pdf:
                fig, ax = plt.subplots(figsize=(12, 12))
                
                # Draw the stock sheet
                sheet_rect = patches.Rectangle(
                    (0, 0), stock_sheet.length, stock_sheet.width,
                    linewidth=2, edgecolor='black', facecolor='white'
                )
                ax.add_patch(sheet_rect)
                
                # Draw each placed panel
                colors = plt.cm.tab20.colors
                for i, placed_panel in enumerate(pattern.placed_panels):
                    panel = placed_panel.panel
                    x, y = placed_panel.x, placed_panel.y
                    
                    # Panel dimensions (considering rotation)
                    if placed_panel.rotated:
                        length, width = panel.width, panel.length
                        rotation_text = " (rotated)"
                    else:
                        length, width = panel.length, panel.width
                        rotation_text = ""
                    
                    # Draw the panel
                    color_idx = i % len(colors)
                    panel_rect = patches.Rectangle(
                        (x, y), length, width,
                        linewidth=1, edgecolor='black', facecolor=colors[color_idx], alpha=0.7
                    )
                    ax.add_patch(panel_rect)
                    
                    # Add label if requested
                    if options.labels_on_panels:
                        label_text = f"{panel.label}{rotation_text}\n{length:.1f} x {width:.1f}"
                        ax.text(
                            x + length/2, y + width/2, label_text,
                            horizontalalignment='center', verticalalignment='center',
                            fontsize=8, fontweight='bold'
                        )
                
                # Set axis limits and labels
                ax.set_xlim(-5, stock_sheet.length + 5)
                ax.set_ylim(-5, stock_sheet.width + 5)
                ax.set_xlabel('Length')
                ax.set_ylabel('Width')
                ax.set_title(f'Cutting Pattern - {stock_sheet.label}')
                
                # Add gridlines
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # Add stats
                used_area = stock_sheet.area() - pattern.waste_area
                usage_percentage = used_area / stock_sheet.area() * 100
                waste_percentage = 100 - usage_percentage
                
                stats_text = (
                    f"Stock Sheet: {stock_sheet.length} x {stock_sheet.width}\n"
                    f"Used Area: {used_area:.2f} ({usage_percentage:.1f}%)\n"
                    f"Waste Area: {pattern.waste_area:.2f} ({waste_percentage:.1f}%)\n"
                    f"Panels Placed: {len(pattern.placed_panels)}\n"
                    f"Kerf Width: {options.kerf_thickness}"
                )
                
                plt.figtext(0.02, 0.02, stats_text, fontsize=10, wrap=True)
                
                # Adjust layout and save to PDF
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close()
            
            # Read the temporary file and encode it as base64
            with open(temp_path, 'rb') as pdf_file:
                pdf_data = base64.b64encode(pdf_file.read())
            
            return pdf_data
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
    def action_open_report(self):
        """Open the cutting pattern report in a new window."""
        self.ensure_one()
        if not self.pattern_pdf:
            raise UserError(_("No cutting pattern PDF is available for this job."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/pattern_pdf/{self.pattern_pdf_filename}?download=true',
            'target': 'new',
        }


class CuttingJobLine(models.Model):
    _name = 'cutting.job.line'
    _description = 'Cutting Job Line'
    _rec_name = 'panel_id'
    
    cutting_job_id = fields.Many2one('cutting.job', string='Cutting Job', required=True, ondelete='cascade')
    panel_id = fields.Many2one('cutting.panel', string='Panel', required=True)
    quantity = fields.Integer('Quantity', required=True, default=1)
    
    # Informational fields from the panel
    length = fields.Float('Length', related='panel_id.length', readonly=True)
    width = fields.Float('Width', related='panel_id.width', readonly=True)
    area = fields.Float('Area', related='panel_id.area', readonly=True)
    
    @api.onchange('panel_id')
    def _onchange_panel_id(self):
        if self.panel_id:
            self.quantity = 1
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise models.ValidationError(_("Quantity must be greater than zero."))
from odoo import models, fields, api


class CuttingPanel(models.Model):
    _name = 'cutting.panel'
    _description = 'Panel for Cutting Stock Optimization'
    _rec_name = 'name'
    _order = 'name, id'
    
    name = fields.Char('Name', required=True, index=True)
    length = fields.Float('Length', required=True, help="Length of the panel in the specified unit")
    width = fields.Float('Width', required=True, help="Width of the panel in the specified unit")
    material_id = fields.Many2one('product.product', string='Material', 
                                domain=[('type', '=', 'product')],
                                help="Material used for this panel")
    grain_direction = fields.Selection([
        ('none', 'No Grain Direction'),
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
    ], string='Grain Direction', default='none', required=True)
    notes = fields.Text('Notes')
    active = fields.Boolean('Active', default=True)
    
    # Used in cutting jobs
    cutting_job_line_ids = fields.One2many('cutting.job.line', 'panel_id', string='Cutting Job Lines')
    
    @api.depends('length', 'width')
    def _compute_area(self):
        for panel in self:
            panel.area = panel.length * panel.width
    
    area = fields.Float('Area', compute='_compute_area', store=True, 
                     help="Area of the panel (length × width)")
    
    @api.constrains('length', 'width')
    def _check_dimensions(self):
        for panel in self:
            if panel.length <= 0 or panel.width <= 0:
                raise models.ValidationError("Panel dimensions must be greater than zero.")
    
    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': f"{self.name} (copy)",
        })
        return super(CuttingPanel, self).copy(default)
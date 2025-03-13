from odoo import models, fields, api


class StockSheet(models.Model):
    _name = 'cutting.stock.sheet'
    _description = 'Stock Sheet for Cutting'
    _rec_name = 'name'
    _order = 'name, id'
    
    name = fields.Char('Name', required=True, index=True)
    length = fields.Float('Length', required=True, help="Length of the stock sheet in the specified unit")
    width = fields.Float('Width', required=True, help="Width of the stock sheet in the specified unit")
    material_id = fields.Many2one('product.product', string='Material', 
                                domain=[('type', '=', 'product')],
                                help="Material of this stock sheet")
    grain_direction = fields.Selection([
        ('none', 'No Grain Direction'),
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
    ], string='Grain Direction', default='none', required=True)
    available_quantity = fields.Integer('Available Quantity', default=1)
    cost = fields.Float('Cost per Sheet', help="Cost per stock sheet")
    notes = fields.Text('Notes')
    active = fields.Boolean('Active', default=True)
    
    # Used in cutting jobs
    cutting_job_ids = fields.One2many('cutting.job', 'stock_sheet_id', string='Cutting Jobs')
    
    @api.depends('length', 'width')
    def _compute_area(self):
        for sheet in self:
            sheet.area = sheet.length * sheet.width
    
    area = fields.Float('Area', compute='_compute_area', store=True, 
                      help="Area of the stock sheet (length × width)")
    
    @api.constrains('length', 'width', 'available_quantity')
    def _check_dimensions(self):
        for sheet in self:
            if sheet.length <= 0 or sheet.width <= 0:
                raise models.ValidationError("Stock sheet dimensions must be greater than zero.")
            if sheet.available_quantity <= 0:
                raise models.ValidationError("Available quantity must be greater than zero.")
    
    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': f"{self.name} (copy)",
        })
        return super(StockSheet, self).copy(default)
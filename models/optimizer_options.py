from odoo import models, fields, api


class OptimizerOptions(models.Model):
    _name = 'cutting.optimizer.options'
    _description = 'Options for Cutting Stock Optimization'
    _rec_name = 'name'
    
    name = fields.Char('Name', required=True, index=True)
    kerf_thickness = fields.Float('Kerf Thickness', default=0.0, 
                                help="Blade thickness or cutting width to account for in the optimization")
    labels_on_panels = fields.Boolean('Show Labels on Panels', default=True, 
                                     help="Show panel labels in the cutting pattern visualization")
    use_single_sheet = fields.Boolean('Use Single Sheet', default=True, 
                                    help="Optimize for a single stock sheet")
    consider_material = fields.Boolean('Consider Material Compatibility', default=True, 
                                     help="Only place panels on compatible stock sheet materials")
    edge_banding = fields.Boolean('Consider Edge Banding', default=False, 
                                help="Take edge banding requirements into account")
    consider_grain = fields.Boolean('Consider Grain Direction', default=False, 
                                   help="Respect grain direction constraints")
    notes = fields.Text('Notes')
    active = fields.Boolean('Active', default=True)
    
    # Used in cutting jobs
    cutting_job_ids = fields.One2many('cutting.job', 'options_id', string='Cutting Jobs')
    
    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': f"{self.name} (copy)",
        })
        return super(OptimizerOptions, self).copy(default)
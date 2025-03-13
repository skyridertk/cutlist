from odoo import api, models


class CuttingPatternReport(models.AbstractModel):
    _name = 'report.cutting_stock_optimizer.report_cutting_pattern'
    _description = 'Cutting Pattern Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Get report values.
        """
        docs = self.env['cutting.job'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'cutting.job',
            'docs': docs,
        }
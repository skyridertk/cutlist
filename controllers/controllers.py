# -*- coding: utf-8 -*-
# from odoo import http


# class Cutlist(http.Controller):
#     @http.route('/cutlist/cutlist', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cutlist/cutlist/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('cutlist.listing', {
#             'root': '/cutlist/cutlist',
#             'objects': http.request.env['cutlist.cutlist'].search([]),
#         })

#     @http.route('/cutlist/cutlist/objects/<model("cutlist.cutlist"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cutlist.object', {
#             'object': obj
#         })


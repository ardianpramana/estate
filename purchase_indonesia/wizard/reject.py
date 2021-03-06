# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 CodUP (<http://codup.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp import netsvc

class QuotationComparisonForm(osv.osv_memory):

    _name = 'quotation.comparison.form.reject'
    _description = 'Reject Request'

    _columns = {
        'reject_reason': fields.text('Reject Reason', required=True),
    }

    def reject_request(self, cr, uid, ids, context=None):
        if 'active_id' in context:
            reject_reason=self.browse(cr,uid,ids)[0].reject_reason
            self.pool.get('quotation.comparison.form').write(cr,uid,context['active_id'],{'reject_reason':reject_reason})
            # wf_service = netsvc.LocalService("workflow")
            qcf = self.pool.get('quotation.comparison.form')
            qcf.action_reject(cr, uid, context['active_id'])
            # wf_service.trg_validate(uid, 'quotation.comparison.form', context['active_id'], 'button_reject', cr)
        return {'type': 'ir.actions.act_window_close',}

class PurchaseRequestReject(osv.osv_memory):

    _name = 'purchase.request.reject'
    _description = 'Reject Request'

    _columns = {
        'reject_reason': fields.text('Reject Reason', required=True),
    }

    def reject_request(self, cr, uid, ids, context=None):
        if 'active_id' in context:
            reject_reason=self.browse(cr,uid,ids)[0].reject_reason
            self.pool.get('purchase.request').write(cr,uid,context['active_id'],{'reject_reason':reject_reason})
            purchase_request = self.pool.get('purchase.request')
            purchase_request.button_rejected(cr, uid, context['active_id'])
        return {'type': 'ir.actions.act_window_close',}
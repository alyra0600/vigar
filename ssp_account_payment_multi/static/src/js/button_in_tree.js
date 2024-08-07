/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { session } from '@web/session';

export class SaleListController extends ListController {
   setup() {
       super.setup();
   }
   OnTestClick() {
       const records = this.model.root.selection;
       const recordIds = records.map((a) => a.resId);

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'account.payment.multi.partial.register.list',
            name: 'Open Wizard',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'current',
            res_id: false,
            context: {
                'active_ids': recordIds,
            },
        });
    }
}

registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: SaleListController,
    buttonTemplate: "button_sale.ListView.Buttons",
});

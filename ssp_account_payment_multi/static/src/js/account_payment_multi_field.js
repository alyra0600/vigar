/** @odoo-module **/

import { AccountPaymentField } from "@account/components/account_payment_field/account_payment_field";
import { patch } from "@web/core/utils/patch";

patch(AccountPaymentField.prototype, {
    async assignOutstandingPartialCredit(moveId, id) {
        const action = await this.orm.call(
            this.props.record.resModel, 
            'action_register_partial_payment', [moveId, id]);
        this.action.doAction(action);
    }
});

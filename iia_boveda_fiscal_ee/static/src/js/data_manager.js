odoo.define('iia_boveda_fiscal_ee.DataManager', function (require) {
"use strict";

	var DataManager = require('web.DataManager');
	var session = require('web.session');
	
	DataManager.include({
		load_action: function (action_id, additional_context) {
			if (additional_context==undefined){
				additional_context={};
			}
			additional_context.allowed_company_ids = session.user_context.allowed_company_ids;
			return this._super(action_id, additional_context);
		}	
	});
});
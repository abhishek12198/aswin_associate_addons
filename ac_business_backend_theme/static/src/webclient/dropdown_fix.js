/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { patch } from "@web/core/utils/patch";

/**
 * Guard against: Cannot read properties of null (reading 'parentElement')
 *
 * AppsMenu closes on ACTION_MANAGER:UI-UPDATED. That notifies all Dropdown
 * listeners via EventBus; some may already be unmounted (this.el is null).
 */
patch(Dropdown.prototype, "ac_business_backend_theme.dropdown_null_guard", {
    onDropdownStateChanged(payload) {
        if (!this.el || !this.el.parentElement) {
            return;
        }
        if (!payload || !payload.emitter || !payload.emitter.el) {
            return;
        }
        return this._super(payload);
    },
});

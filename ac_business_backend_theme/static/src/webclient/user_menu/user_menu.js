/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

const ALLOWED_USER_MENU_IDS = new Set(["settings", "logout"]);

patch(UserMenu.prototype, "ac_business_backend_theme.UserMenu", {
    getElements() {
        return this._super(...arguments).filter(
            (item) => item.type === "item" && ALLOWED_USER_MENU_IDS.has(item.id)
        );
    },
});

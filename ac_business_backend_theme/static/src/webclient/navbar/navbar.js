/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

import { NavBar } from "@web/webclient/navbar/navbar";
import { AppsMenu } from "@ac_business_backend_theme/webclient/appsmenu/appsmenu";
import { AppsBar } from "@ac_business_backend_theme/webclient/appsbar/appsbar";

patch(NavBar, "ac_business_backend_theme.NavBar", {
    components: {
        ...NavBar.components,
        AppsMenu,
        AppsBar,
    },
});

patch(NavBar.prototype, "ac_business_backend_theme.NavBar.company", {
    setup() {
        this._super(...arguments);
        this.companyName = session.company_name || "";
        this.companyLogoUrl = session.company_logo_url || "/web/binary/company_logo";
    },
});

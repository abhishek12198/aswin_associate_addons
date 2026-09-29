/** @odoo-module **/

import { titleService } from "@web/core/browser/title_service";
import { session } from "@web/session";

const _origStart = titleService.start.bind(titleService);

titleService.start = function () {
    const service = _origStart();
    const appTitle = session.app_title || session.company_name || "Odoo";
    const _origSetParts = service.setParts.bind(service);
    service.setParts = (parts) => {
        if (parts && Object.prototype.hasOwnProperty.call(parts, "zopenerp")) {
            const val = parts.zopenerp;
            if (!val || val === "Odoo") {
                parts = { ...parts, zopenerp: appTitle };
            }
        }
        return _origSetParts(parts);
    };
    return service;
};

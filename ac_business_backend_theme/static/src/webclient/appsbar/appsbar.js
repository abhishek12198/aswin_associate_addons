/** @odoo-module **/

const { Component } = owl;

export class AppsBar extends Component {
    getAppHref(app) {
        let href = `#menu_id=${app.id}`;
        if (app.actionID) {
            href += `&action_id=${app.actionID}`;
        }
        return href;
    }
}

Object.assign(AppsBar, {
    template: "ac_business_backend_theme.AppsBar",
    props: {
        apps: Array,
        currentApp: { type: Object, optional: true },
        companyName: { type: String, optional: true },
        companyLogoUrl: { type: String, optional: true },
    },
});

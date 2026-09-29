/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { symmetricalDifference } from "@web/core/utils/arrays";
import { _t } from "@web/core/l10n/translation";

const { Component, hooks } = owl;
const { useState } = hooks;

export class AcSwitchCompanyMenu extends Component {
    setup() {
        this.companyService = useService("company");
        this.currentCompany = this.companyService.currentCompany;
        this.state = useState({ companiesToToggle: [] });
    }

    get hasMultipleCompanies() {
        return Object.keys(this.companyService.availableCompanies).length > 1;
    }

    getCompanyLogoUrl(company) {
        return company.logo_url || `/web/binary/company_logo?company=${company.id}`;
    }

    toggleCompany(companyId) {
        this.state.companiesToToggle = symmetricalDifference(this.state.companiesToToggle, [
            companyId,
        ]);
        browser.clearTimeout(this.toggleTimer);
        this.toggleTimer = browser.setTimeout(() => {
            this.companyService.setCompanies("toggle", ...this.state.companiesToToggle);
        }, this.constructor.toggleDelay);
    }

    logIntoCompany(companyId) {
        browser.clearTimeout(this.toggleTimer);
        this.companyService.setCompanies("loginto", companyId);
    }

    get selectedCompanies() {
        return symmetricalDifference(
            this.companyService.allowedCompanyIds,
            this.state.companiesToToggle
        );
    }

    get hasMultipleSelected() {
        return this.selectedCompanies.length > 1;
    }

    get togglerLabel() {
        if (this.hasMultipleSelected) {
            return _t("Multiple Companies");
        }
        return this.companyService.currentCompany.name;
    }
}

AcSwitchCompanyMenu.template = "ac_business_backend_theme.AcSwitchCompanyMenu";
AcSwitchCompanyMenu.components = { Dropdown, DropdownItem };
AcSwitchCompanyMenu.toggleDelay = 1000;

export const systrayItem = {
    Component: AcSwitchCompanyMenu,
    isDisplayed() {
        return true;
    },
};

registry.category("systray").remove("SwitchCompanyMenu");
registry.category("systray").add(
    "ac_business_backend_theme.SwitchCompanyMenu",
    systrayItem,
    { sequence: 60 }
);

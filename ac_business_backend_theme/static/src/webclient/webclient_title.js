/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { session } from "@web/session";
import { useBus, useEffect } from "@web/core/utils/hooks";

/**
 * Dismiss the branded splash as soon as the shell is usable.
 * Do not wait for the home/landing action — that can take many seconds
 * and makes login feel blocked behind the loader.
 */
let bootSplashDismissed = false;

function dismissBootSplash() {
    if (bootSplashDismissed) {
        return;
    }
    bootSplashDismissed = true;
    const el = document.getElementById("ac-boot-splash");
    const finish = () => {
        if (el) {
            el.remove();
        }
        const critical = document.getElementById("ac-boot-critical");
        if (critical) {
            critical.remove();
        }
        document.documentElement.classList.remove("ac-booting");
    };
    if (el) {
        el.classList.add("ac-boot-gone");
        setTimeout(finish, 120);
    } else {
        finish();
    }
}

function watchForShellReady() {
    if (document.querySelector(".o_main_navbar")) {
        dismissBootSplash();
        return null;
    }
    const observer = new MutationObserver(() => {
        if (document.querySelector(".o_main_navbar")) {
            observer.disconnect();
            requestAnimationFrame(() => dismissBootSplash());
        }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    return observer;
}

patch(WebClient.prototype, "ac_business_backend_theme.WebClientTitle", {
    setup() {
        const appTitle = session.app_title || session.company_name || "Odoo";
        this._super(...arguments);
        this.title.setParts({ zopenerp: appTitle });

        useEffect(
            () => {
                const observer = watchForShellReady();
                // Hard fallback after Owl starts — splash must not wait on home action.
                const timeout = setTimeout(dismissBootSplash, 800);
                return () => {
                    if (observer) {
                        observer.disconnect();
                    }
                    clearTimeout(timeout);
                };
            },
            () => []
        );

        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", (mode) => {
            if (mode === "new") {
                return;
            }
            requestAnimationFrame(() => dismissBootSplash());
        });
    },
});

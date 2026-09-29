odoo.define('ac_customer_receivable.KanbanColumn', function (require) {
    "use strict";

    var KanbanColumn = require('web.KanbanColumn');

    KanbanColumn.include({
        /**
         * Prevent drag-start on Done / Declined service engagement cards.
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var $el = self.$el;
                if (!$el.data('ui-sortable')) {
                    return;
                }
                var cancel = $el.sortable('option', 'cancel') || 'input,textarea,button,a';
                if (cancel.indexOf('o_ac_job_kanban_frozen') === -1) {
                    $el.sortable('option', 'cancel', cancel + ', .o_ac_job_kanban_frozen');
                }
            });
        },
    });
});

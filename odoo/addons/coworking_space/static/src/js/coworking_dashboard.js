/* Coworking Space Dashboard JavaScript */

odoo.define('coworking_space.dashboard', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');

    var CoworkingDashboard = Widget.extend({
        template: 'coworking_space.dashboard',
        
        init: function(parent, options) {
            this._super.apply(this, arguments);
            this.options = options || {};
        },
        
        start: function() {
            this._super.apply(this, arguments);
            this._loadDashboardData();
        },
        
        _loadDashboardData: function() {
            // Load dashboard statistics
            console.log('Loading coworking dashboard data...');
        },
    });

    return CoworkingDashboard;
});

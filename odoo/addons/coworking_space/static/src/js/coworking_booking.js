/* Coworking Space Booking JavaScript */

odoo.define('coworking_space.booking', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;

    // Room Booking Widget
    publicWidget.registry.CoworkingBooking = publicWidget.Widget.extend({
        selector: '.coworking-booking-form',
        events: {
            'change #room_select': '_onRoomChange',
            'change #booking_date': '_onDateChange',
            'click .time-slot.available': '_onTimeSlotClick',
            'click #btn_book_room': '_onBookRoom',
        },

        start: function () {
            this._super.apply(this, arguments);
            this._loadAvailableSlots();
        },

        _onRoomChange: function () {
            this._loadAvailableSlots();
        },

        _onDateChange: function () {
            this._loadAvailableSlots();
        },

        _onTimeSlotClick: function (ev) {
            var $slot = $(ev.currentTarget);
            
            // Clear previous selections
            this.$('.time-slot').removeClass('selected');
            
            // Select clicked slot
            $slot.addClass('selected');
            
            // Update form fields
            this.$('#start_datetime').val($slot.data('start'));
            this.$('#end_datetime').val($slot.data('end'));
            
            // Enable booking button
            this.$('#btn_book_room').prop('disabled', false);
        },

        _onBookRoom: function (ev) {
            ev.preventDefault();
            
            var formData = {
                room_id: parseInt(this.$('#room_select').val()),
                start_datetime: this.$('#start_datetime').val(),
                end_datetime: this.$('#end_datetime').val(),
                purpose: this.$('#purpose').val(),
                attendees_count: parseInt(this.$('#attendees_count').val()) || 1,
                name: this.$('#customer_name').val(),
                email: this.$('#customer_email').val(),
                phone: this.$('#customer_phone').val(),
            };

            // Validate required fields
            if (!formData.room_id || !formData.start_datetime || !formData.end_datetime) {
                this._showAlert('error', _t('Please select a room and time slot.'));
                return;
            }

            // Show loading
            this.$('#btn_book_room').prop('disabled', true).text(_t('Booking...'));

            // Submit booking
            ajax.jsonRpc('/coworking/api/booking/create', 'call', formData)
                .then(this._onBookingSuccess.bind(this))
                .catch(this._onBookingError.bind(this));
        },

        _onBookingSuccess: function (result) {
            if (result.success) {
                this._showAlert('success', result.message);
                this._resetForm();
                this._loadAvailableSlots(); // Refresh availability
            } else {
                this._showAlert('error', result.error || _t('Booking failed.'));
            }
            this.$('#btn_book_room').prop('disabled', false).text(_t('Book Room'));
        },

        _onBookingError: function (error) {
            console.error('Booking error:', error);
            this._showAlert('error', _t('An error occurred. Please try again.'));
            this.$('#btn_book_room').prop('disabled', false).text(_t('Book Room'));
        },

        _loadAvailableSlots: function () {
            var roomId = parseInt(this.$('#room_select').val());
            var date = this.$('#booking_date').val();
            
            if (!roomId || !date) {
                return;
            }

            var duration = parseFloat(this.$('#duration').val()) || 1;

            ajax.jsonRpc('/coworking/api/room/slots', 'call', {
                room_id: roomId,
                date: date,
                duration: duration
            }).then(this._renderTimeSlots.bind(this));
        },

        _renderTimeSlots: function (result) {
            var $container = this.$('.time-slots-container');
            $container.empty();

            if (result.error) {
                $container.html('<div class="alert alert-warning">' + result.error + '</div>');
                return;
            }

            if (!result.slots || result.slots.length === 0) {
                $container.html('<div class="alert alert-info">' + _t('No available slots for this date.') + '</div>');
                return;
            }

            var slotsHtml = '<div class="row">';
            result.slots.forEach(function (slot) {
                var startTime = new Date(slot.start).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                var endTime = new Date(slot.end).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                
                slotsHtml += '<div class="col-md-3 col-sm-4 col-6 mb-2">';
                slotsHtml += '<div class="time-slot available" data-start="' + slot.start + '" data-end="' + slot.end + '">';
                slotsHtml += startTime + ' - ' + endTime;
                slotsHtml += '</div>';
                slotsHtml += '</div>';
            });
            slotsHtml += '</div>';

            $container.html(slotsHtml);
        },

        _resetForm: function () {
            this.$('form')[0].reset();
            this.$('.time-slot').removeClass('selected');
            this.$('#btn_book_room').prop('disabled', true);
        },

        _showAlert: function (type, message) {
            var alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
            var alertHtml = '<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert">';
            alertHtml += message;
            alertHtml += '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
            alertHtml += '</div>';
            
            this.$('.alerts-container').html(alertHtml);
            
            // Auto-hide success alerts
            if (type === 'success') {
                setTimeout(function () {
                    $('.alert-success').fadeOut();
                }, 5000);
            }
        },
    });

    // Event Registration Widget
    publicWidget.registry.EventRegistration = publicWidget.Widget.extend({
        selector: '.event-registration-form',
        events: {
            'click #btn_register_event': '_onRegisterEvent',
        },

        _onRegisterEvent: function (ev) {
            ev.preventDefault();
            
            var eventId = parseInt(this.$('#event_id').val());
            
            if (!eventId) {
                this._showAlert('error', _t('Invalid event.'));
                return;
            }

            // Show loading
            this.$('#btn_register_event').prop('disabled', true).text(_t('Registering...'));

            // Submit registration
            ajax.jsonRpc('/coworking/api/event/register', 'call', {
                event_id: eventId
            }).then(this._onRegistrationSuccess.bind(this))
              .catch(this._onRegistrationError.bind(this));
        },

        _onRegistrationSuccess: function (result) {
            if (result.success) {
                this._showAlert('success', result.message);
                if (result.price > 0) {
                    // Redirect to payment if required
                    window.location.href = '/payment/event/' + result.registration_id;
                }
            } else {
                this._showAlert('error', result.error || _t('Registration failed.'));
            }
            this.$('#btn_register_event').prop('disabled', false).text(_t('Register'));
        },

        _onRegistrationError: function (error) {
            console.error('Registration error:', error);
            this._showAlert('error', _t('An error occurred. Please try again.'));
            this.$('#btn_register_event').prop('disabled', false).text(_t('Register'));
        },

        _showAlert: function (type, message) {
            var alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
            var alertHtml = '<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert">';
            alertHtml += message;
            alertHtml += '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
            alertHtml += '</div>';
            
            this.$('.alerts-container').html(alertHtml);
        },
    });

    // Room Availability Checker
    publicWidget.registry.RoomAvailability = publicWidget.Widget.extend({
        selector: '.room-availability-checker',
        events: {
            'click #check_availability': '_onCheckAvailability',
        },

        _onCheckAvailability: function (ev) {
            ev.preventDefault();
            
            var roomId = parseInt(this.$('#room_id').val());
            var startDatetime = this.$('#start_datetime').val();
            var endDatetime = this.$('#end_datetime').val();
            
            if (!roomId || !startDatetime || !endDatetime) {
                this._showResult('error', _t('Please fill all fields.'));
                return;
            }

            ajax.jsonRpc('/coworking/api/room/availability', 'call', {
                room_id: roomId,
                start_datetime: startDatetime,
                end_datetime: endDatetime
            }).then(this._onAvailabilityResult.bind(this));
        },

        _onAvailabilityResult: function (result) {
            if (result.error) {
                this._showResult('error', result.error);
            } else if (result.available) {
                this._showResult('success', _t('Room is available!'));
            } else {
                this._showResult('warning', _t('Room is not available for the selected time.'));
            }
        },

        _showResult: function (type, message) {
            var alertClass = 'alert-' + (type === 'error' ? 'danger' : type);
            var resultHtml = '<div class="alert ' + alertClass + '">' + message + '</div>';
            this.$('.availability-result').html(resultHtml);
        },
    });

    return {
        CoworkingBooking: publicWidget.registry.CoworkingBooking,
        EventRegistration: publicWidget.registry.EventRegistration,
        RoomAvailability: publicWidget.registry.RoomAvailability,
    };
});

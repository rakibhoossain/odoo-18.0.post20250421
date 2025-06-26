# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestCoworkingMembership(TransactionCase):

    def setUp(self):
        super(TestCoworkingMembership, self).setUp()
        
        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Member',
            'email': 'test@example.com',
            'phone': '+1234567890',
        })
        
        # Create test membership plans
        self.unlimited_plan = self.env['coworking.membership.plan'].create({
            'name': 'Unlimited Plan',
            'code': 'unlimited',
            'monthly_price': 20.0,
            'coworking_access': 'free',
            'meeting_room_access': 'free',
            'event_access': 'free',
        })
        
        self.payg_plan = self.env['coworking.membership.plan'].create({
            'name': 'Pay-As-You-Go',
            'code': 'payg',
            'monthly_price': 10.0,
            'credit_amount': 10.0,
            'coworking_access': 'credit',
            'meeting_room_access': 'paid',
            'event_access': 'paid',
        })

    def test_membership_creation(self):
        """Test membership creation and basic functionality"""
        membership = self.env['coworking.membership'].create({
            'partner_id': self.partner.id,
            'plan_id': self.unlimited_plan.id,
            'start_date': datetime.now().date(),
        })
        
        self.assertEqual(membership.state, 'draft')
        self.assertEqual(membership.partner_id, self.partner)
        self.assertEqual(membership.plan_id, self.unlimited_plan)
        self.assertTrue(membership.name.startswith('MEM'))

    def test_membership_activation(self):
        """Test membership activation"""
        membership = self.env['coworking.membership'].create({
            'partner_id': self.partner.id,
            'plan_id': self.unlimited_plan.id,
            'start_date': datetime.now().date(),
        })
        
        membership.action_activate()
        self.assertEqual(membership.state, 'active')

    def test_payg_credit_system(self):
        """Test Pay-As-You-Go credit system"""
        membership = self.env['coworking.membership'].create({
            'partner_id': self.partner.id,
            'plan_id': self.payg_plan.id,
            'start_date': datetime.now().date(),
        })
        
        membership.action_activate()
        
        # Check initial credit
        self.assertEqual(membership.credit_balance, 10.0)
        self.assertEqual(membership.initial_credit, 10.0)
        
        # Test credit consumption
        self.assertTrue(membership.check_credit_balance(5.0))
        membership.consume_credit(5.0)
        self.assertEqual(membership.credit_balance, 5.0)
        
        # Test insufficient credit
        self.assertFalse(membership.check_credit_balance(10.0))
        with self.assertRaises(ValidationError):
            membership.consume_credit(10.0)

    def test_membership_renewal(self):
        """Test membership renewal"""
        membership = self.env['coworking.membership'].create({
            'partner_id': self.partner.id,
            'plan_id': self.payg_plan.id,
            'start_date': datetime.now().date(),
            'end_date': datetime.now().date() + timedelta(days=30),
        })
        
        membership.action_activate()
        membership.consume_credit(5.0)  # Use some credit
        
        membership.action_renew()
        
        # Check that credit is reset for Pay-As-You-Go plans
        self.assertEqual(membership.credit_balance, 10.0)
        self.assertEqual(membership.state, 'active')

    def test_partner_membership_integration(self):
        """Test partner integration with membership"""
        membership = self.env['coworking.membership'].create({
            'partner_id': self.partner.id,
            'plan_id': self.unlimited_plan.id,
            'start_date': datetime.now().date(),
        })
        
        membership.action_activate()
        
        # Test partner computed fields
        self.assertTrue(self.partner.is_coworking_member)
        self.assertEqual(self.partner.active_membership_id, membership)
        self.assertEqual(self.partner.member_since, membership.start_date)
        
        # Test access methods
        self.assertEqual(self.partner.get_membership_plan_access('coworking'), 'free')
        self.assertTrue(self.partner.has_free_access('meeting_room'))

    def test_plan_unique_code(self):
        """Test that plan codes must be unique"""
        with self.assertRaises(ValidationError):
            self.env['coworking.membership.plan'].create({
                'name': 'Duplicate Plan',
                'code': 'unlimited',  # Same as existing plan
                'monthly_price': 15.0,
                'coworking_access': 'free',
                'meeting_room_access': 'paid',
                'event_access': 'paid',
            })

    def test_membership_statistics(self):
        """Test membership statistics computation"""
        membership = self.env['coworking.membership'].create({
            'partner_id': self.partner.id,
            'plan_id': self.unlimited_plan.id,
            'start_date': datetime.now().date(),
        })
        
        membership.action_activate()
        
        # Initially no bookings or usage
        self.assertEqual(membership.total_bookings, 0)
        self.assertEqual(membership.total_hours_used, 0)
        
        # Create a usage record
        self.env['coworking.usage'].create({
            'membership_id': membership.id,
            'usage_type': 'coworking',
            'date': datetime.now().date(),
            'hours': 8.0,
            'description': 'Test usage',
        })
        
        # Check statistics update
        self.assertEqual(membership.total_hours_used, 8.0)

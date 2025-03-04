# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    Autor: Brayhan Andres Jaramillo Castaño
#    Correo: brayhanjaramillo@hotmail.com
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import logging
import werkzeug
from odoo import http, _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class AuthSignupHome(AuthSignupHome):

	def do_signup(self, qcontext):
		""" Shared helper that creates a res.partner out of a token """
		values = {key: qcontext.get(key) for key in (
			'login', 'name', 'password', 'x_name1', 'x_lastname1')}
		if not values:
			raise UserError(_("The form was not properly filled in."))
		if values.get('password') != qcontext.get('confirm_password'):
			raise UserError(_("Passwords do not match; please retype them."))
		supported_langs = [lang['code'] for lang in request.env[
			'res.lang'].sudo().search_read([], ['code'])]
		if request.lang in supported_langs:
			values['lang'] = request.lang
		self._signup_with_values(qcontext.get('token'), values)
		request.env.cr.commit()

	@http.route('/web/signup', type='http', auth='public', website=True,
				sitemap=False)
	def web_auth_signup(self, *args, **kw):
		qcontext = self.get_auth_signup_qcontext()


		if not qcontext.get('token') and not qcontext.get('signup_enabled'):
			raise werkzeug.exceptions.NotFound()

		if 'error' not in qcontext and request.httprequest.method == 'POST':
			try:
				self.do_signup(qcontext)
				# Send an account creation confirmation email
				if qcontext.get('token'):
					user_sudo = request.env['res.users'].sudo().search(
						[('login', '=', qcontext.get('login'))])
					template = request.env.ref(
						'auth_signup.mail_template_user_signup_account_created',
						raise_if_not_found=False)
					if user_sudo and template:
						template.sudo().with_context(
							lang=user_sudo.lang,
							auth_login=werkzeug.url_encode({
								'auth_login': user_sudo.email
							}),
						).send_mail(user_sudo.id, force_send=True)
				return super(AuthSignupHome, self).web_login(*args, **kw)
			except UserError as e:
				qcontext['error'] = e.name or e.value
			except (SignupError, AssertionError) as e:
				if request.env["res.users"].sudo().search(
						[("login", "=", qcontext.get("login"))]):
					qcontext["error"] = _(
						"Another user is already registered using this email address.")
				else:
					_logger.error("%s", e)
					qcontext['error'] = _("Could not create a new account.")

		response = request.render('auth_signup.signup', qcontext)
		response.headers['X-Frame-Options'] = 'DENY'
		return response


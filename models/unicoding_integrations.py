
import requests
from odoo import _, api, fields, models
from datetime import date
from datetime import datetime
import json
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

URLOPEN_TIMEOUT = 10



class UnicodingIntegrations(models.Model):
    _inherit = 'unicoding.integrations'

    url = fields.Char(string="API URL")

    _access_token = fields.Char(string="access_token")

    _token_datetime = fields.Datetime(string="Token Datetime")

    api_username = fields.Char(string="API Name")
    api_key = fields.Char(string="API Key")

    last_item_date = fields.Date(string='Update Date', default='2000-01-01')

    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company.id, required=True)




    def _get_token(self):
        opencart_id = self.get_integration_details()
        params = {
            'username': opencart_id.api_username,
            'key': opencart_id.api_key,
        }
        headers = {"content-type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post("%s/index.php?route=api/login&api_token=" % (opencart_id.url), data=params, headers=headers)

            result = response.json()

            opencart_id._access_token = result["api_token"] if "api_token" in result.keys() else result["token"]

            opencart_id._token_datetime = datetime.now()

            opencart_id.message_post(
                body=_(
                    'Sussecss getting token %s datetime %s'
                ) % (opencart_id._access_token, str(opencart_id._token_datetime)),
                subject=_(
                    'Issue with Online OpenCart'
                ),
            )
            return result

        except Exception as e:
            #print(response.content)
            opencart_id.message_post(body=_('Failed to connect with error %s' % str(e)), subject= _('Issue with connection'))
            return False







    def _get_orders(self):
        opencart_id = self.get_integration_details()


        params = {
            'date': self.last_item_date.strftime("%Y-%m-%d"),
            'limit': 100,
            'api_token': opencart_id._access_token,
            'token': opencart_id._access_token
        }


        headers = {"content-type": "application/x-www-form-urlencoded"}
        try:
            response = requests.get("%s/index.php?route=api/integrations/orders" % (opencart_id.url), params=params, headers=headers)
            print(response.content)
            #if response.ok:
            result = response.json()
            if "error" not in result.keys():
                return result['orders']
            else:
                opencart_id.message_post(
                    body=_(
                        'Failed to get order with error %s. See server logs for  more details.'
                    ) % str(result["error"]),
                    subject=_(
                        'Issue with Connection'
                    ),
                )
        except Exception as e:
            opencart_id.message_post(body=_('Failed to get orders %s' % str(e)), subject=_('Issue with connection'))

        return {}

    def add_coupon(self, name):
        ProductTemplate = self.env['product.template']
        coupon_id = ProductTemplate.search([('name', '=', name)], limit=1)

        if not coupon_id:
            coupon_id = ProductTemplate.create({
                'name': name,
                'type': 'service',
                'categ_id': self.env.ref('product.product_category_3').id,
                # 'attribute_line_ids': attribute_line_ids
            })

        return coupon_id.product_variant_id



    def action_getorders(self):
        opencart_id = self.get_integration_details()
        print('-------------------------------------------------------')


        Partner = self.env['res.partner']
        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']
        СrmLead = self.env['crm.lead']
        ResCountryState = self.env['res.country.state']
        ResCountry = self.env['res.country']
        ResCurrency = self.env['res.currency']
        CrmTeam = self.env['crm.team']
        ProductTemplate = self.env['product.template']
        ProductProduct = self.env['product.product']
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        ProductTemplateAttributeValue = self.env['product.template.attribute.value']
        ProductTemplateAttributeLine = self.env['product.template.attribute.line']
        ProductCategory = self.env['product.category']
        ProductPricelist = self.env['product.pricelist']
        ProductPricelistItem = self.env['product.pricelist.item']
        AccountTax = self.env['account.tax']



        #check parameters
        self._get_token()

        #print(self.env.company.group_product_variant)
        # print(">>>>>>>>>>>>>>>>>>>>>>>>")
        # print(self.env['ir.config_parameter'].sudo().get_param('product.group_product_variant'))
        # print("<<<<<<<<<<<<<<<<<<<<<<<<")
        # # print(self._get_orders())
        #return True


        currency_id = self.env.company.currency_id
        orders = self._get_orders()

        #return True
        orders_amount = 0
        for key, order in orders.items() if orders else []:
            #try:



            saleorder_id = SaleOrder.search(
                [('opencartid', '=', order['order_id']), ('unicoding_integrations_id', '=', self.id)], limit=1)



            if saleorder_id:
                continue

            orders_amount += 1

            self.last_item_date = order['date_added']


            #print(order)
            # create partner if not exists
            if order["customer_id"]:
                partner_id = Partner.search(
                    [('opencartid', '=', order['customer_id']), ('unicoding_integrations_id', '=', self.id)], limit=1)
            if not partner_id and order['telephone']:
                partner_id = Partner.search(
                    [('mobile', '=', order['telephone']), ('unicoding_integrations_id', '=', self.id)], limit=1)
            if not partner_id and order['firstname'] != 'Заказ' and (order['firstname'] or order['lastname']):
                partner_id = Partner.search([('name', 'ilike', order['firstname'] + ' ' + order['lastname']),
                                             ('unicoding_integrations_id', '=', self.id)], limit=1)

            # create partner

            partner_country_id = ResCountry.search([('code', '=', order['shipping_iso_code_2'])])

            if not partner_id:
                partner_id = Partner.create({
                    'name': order['firstname'] + ' ' + order['lastname'],
                    "company_type": 'person',
                    "opencartid": order['customer_id'],
                    "mobile": order['telephone'],
                    "email": order['email'],
                    'create_date': order['date_added'],
                    'child_ids': [[0, False, {
                        'type': 'delivery',
                        'name': order['shipping_firstname'] + ' ' + order['shipping_lastname'],
                        'street': order['shipping_address_1'],
                        'street2': order['shipping_address_2'],
                        'city': order['shipping_city'],
                        'state_id': ResCountryState.search([('code', '=', order['shipping_zone_code']),
                                                            ('country_id', '=', partner_country_id.id)]).id,
                        'zip': order['shipping_postcode'],
                        'country_id': partner_country_id.id,
                        "email": order['email'],
                        "mobile": order['telephone'],
                        'create_date': order['date_added'],
                    }]]
                })

            from_currency_id = ResCurrency.with_context(active_test=False).search([('name', '=', order['currency_code'])])
            if not from_currency_id.active:
                from_currency_id.active = True



            # products add

            productpricelist_id = ProductPricelist.search(
                [('name', '=', from_currency_id.name), ('currency_id', '=', from_currency_id.id)])
            if not productpricelist_id:
                productpricelist_id = ProductPricelist.create({
                    'name': from_currency_id.name,
                    'currency_id': from_currency_id.id
                })

            if not saleorder_id:
                saleorder_id = SaleOrder.create({
                    'partner_id': partner_id.id,
                    'date_order': order['date_added'],
                    "opencartid": order['order_id'],
                    "unicoding_integrations_id": self.id,
                    'team_id': CrmTeam.search([('name', '=', order['payment_country'])]).id,
                    'pricelist_id': productpricelist_id.id,
                    'create_date': order['date_added']
                })

            subtotal = 0
            print(order['products'])
            for pkey, product in order['products'].items() if order["products"] else []:

                manufacturer_id = Partner.search(
                    [('opencartid', '=', product['manufacturer']), ('is_company', '=', True)], limit=1)

                if not manufacturer_id and product['manufacturer']:
                    manufacturer_id = Partner.create({
                        'name': product['manufacturer'],
                        "company_type": 'company',
                        "is_company": True,
                        "opencartid": product['manufacturer'],
                        'property_purchase_currency_id': currency_id.id
                    })

                product_tmpl_id = ProductTemplate.search(
                    [('default_code', '=', product['product_id'])])

                if not product_tmpl_id:
                    product_tmpl_id = ProductTemplate.create({
                        'name': product['name'],
                        'default_code': product['product_id'],
                        'type': 'product',
                        # 'categ_id': category_id.id,
                        'seller_ids':[(0, False, {'name': manufacturer_id.id, 'delay': 1, 'min_qty': 1, 'price': 0,
                                                   'currency_id': currency_id.id})] if manufacturer_id else [],
                        # 'attribute_line_ids': attribute_line_ids
                    })

                category_id = ProductCategory.search([('name', '=', product['category'])])
                if not category_id and product['category']:
                    category_id = ProductCategory.create({
                        'name': product['category'],
                        'parent_id': self.env.ref('product.product_category_1').id,
                        'property_cost_method': 'average',
                        'property_valuation': 'real_time'
                    })

                    product_tmpl_id.categ_id = category_id.id

                attribute_ids = []
                value_ids = []

                # choice next product
                #if not product['options']:
                #    continue


                for option in product['options']:

                    attribute_id = ProductAttribute.search([('name', '=', option['name'])])
                    if not attribute_id:
                        attribute_id = ProductAttribute.create({
                            'name': option['name']
                        })

                    value_id = ProductAttributeValue.search(
                        [('attribute_id', '=', attribute_id.id), ('name', '=', option['value'])], limit=1)
                    if not value_id:
                        value_id = ProductAttributeValue.create(
                            {'name': option['value'], 'attribute_id': attribute_id.id})

                    ptal_id = ProductTemplateAttributeLine.search([('product_tmpl_id', '=', product_tmpl_id.id), ('attribute_id', '=', attribute_id.id)], limit=1)
                    if not ptal_id:
                        ptal_id = ProductTemplateAttributeLine.create({
                            'product_tmpl_id': product_tmpl_id.id,
                            'attribute_id': attribute_id.id,
                            'value_ids': [(6, 0, [value_id.id])]
                        })
                    else:
                        ptal_id.write({'value_ids': [(4, value_id.id)]})




                    attribute_ids.append(attribute_id.id)
                    value_ids.append(value_id.id)


                combination = ProductTemplateAttributeValue.search( [('attribute_id', 'in', attribute_ids), ('product_tmpl_id', '=',  product_tmpl_id.id), ('product_attribute_value_id', 'in', value_ids)], limit=1)

                #product_id = product_tmpl_id._get_variant_for_combination(combination)
                product_id = ProductProduct.search([('product_tmpl_id', '=', product_tmpl_id.id), ('product_template_attribute_value_ids', '=', combination.id)],
                                                            limit=1)
                tax_ids = []
                tax_ids_coupons = []
                if "rates" in product.keys():
                    for prate, rate in product["rates"].items() if product["rates"] else []:
                        print(rate)
                        tax_name = rate['name']
                        tax_id = AccountTax.search(
                            [('name', '=', tax_name)])
                        if not tax_id and tax_name:
                            tax_id = AccountTax.create({
                                'name': tax_name,
                                'amount': rate['rate'],
                                'price_include': False, # if order['config_tax']=='1' else False,
                                'amount_type': "fixed" if rate['type'] == "F" else "percent",
                                'active': True
                            })

                        tax_ids.append(tax_id.id)
                        if rate['type'] == "P":
                            tax_ids_coupons.append(tax_id.id)


                product_id.write({'default_code': product['product_id']})



                price_unit = from_currency_id._convert(float(product['price']) * float(order['currency_value']),
                                                       from_currency_id, self.env.company, order['date_added'])



                SaleOrderLine.create({
                    'order_id': saleorder_id.id,
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_uom': product_id.uom_id.id,
                    'product_uom_qty': product['quantity'],
                    'price_unit': price_unit,
                    'tax_id':  [(6, 0, tax_ids)],
                })

                subtotal += float(product['total'])

                ProductPricelistItem.create(
                    {'name': product_tmpl_id.name, 'date_start': order['date_added'], 'applied_on': '1_product',
                     'product_tmpl_id': product_tmpl_id.id, 'fixed_price': price_unit,
                     'pricelist_id': productpricelist_id.id})


            if "totals" in order:
                for total in order["totals"]:
                    if total['code'] == 'coupon':
                        coupon_id = self.add_coupon(total['title'])
                        SaleOrderLine.create({
                            'order_id': saleorder_id.id,
                            'name': coupon_id.name,
                            'product_id': coupon_id.id,
                            'product_uom': coupon_id.uom_id.id,
                            'product_uom_qty': 1,
                            'price_unit': total['value'],
                            'tax_id': [(6, 0, tax_ids_coupons)],
                        })

                    if total['code'] == 'voucher':
                        coupon_id = self.add_coupon(total['title'])
                        SaleOrderLine.create({
                            'order_id': saleorder_id.id,
                            'name': coupon_id.name,
                            'product_id': coupon_id.id,
                            'product_uom': coupon_id.uom_id.id,
                            'product_uom_qty': 1,
                            'price_unit': total['value'],
                            'tax_id': [],
                        })

                    if total['code'] == 'shipping':
                        print(total)
                        delivery_carrier_id = self.env['delivery.carrier'].search(
                            [('name', '=', total['title']), ('delivery_type', '=', 'fixed')])

                        if not delivery_carrier_id:
                            delivery_template_id = ProductTemplate.create({
                                'name': total['title'],
                                'type': 'service',
                                'categ_id': self.env.ref('delivery.product_category_deliveries').id,
                                'taxes_id': [(6, 0, tax_ids)]
                                # 'attribute_line_ids': attribute_line_ids
                            })
                            delivery_product_id = ProductProduct.search([('product_tmpl_id', '=', delivery_template_id.id)], limit=1)

                            #delivery_template_id._create_variant_ids()
                            delivery_carrier_id = self.env['delivery.carrier'].create({
                                'name': total['title'],
                                'delivery_type': 'fixed',
                                'product_id': delivery_product_id.id,
                            })

                        # if found carreir
                        if delivery_carrier_id:
                            print(delivery_carrier_id)
                            delivery_carrier_id.product_id.write({
                                'taxes_id': [(6, 0, tax_ids)]
                            })

                            saleorder_id.set_delivery_line(delivery_carrier_id, from_currency_id._convert(
                                (float(total['value'])) * float(order['currency_value']), from_currency_id,
                                self.env.company, order['date_added']))
                            saleorder_id.write({
                                'recompute_delivery_price': False,
                                'delivery_message': total['title'],
                            })

            # CRM add
            print(order['date_added'])
            lead_id = СrmLead.search(
                [('opencartid', '=', order['order_id']), ('unicoding_integrations_id', '=', self.id)], limit=1)

            if not lead_id:
                lead_id = СrmLead.create({
                    'name': _('Order') + ' ' + order['order_id'],
                    'expected_revenue': from_currency_id._convert(float(order['total']) * float(order['currency_value']),
                                                                 currency_id, self.env.company, order['date_added']),
                    'email_from': order['email'],
                    'phone': order['telephone'],
                    'partner_id': partner_id.id,
                    'team_id': CrmTeam.search([('name', '=', order['payment_country'])]).id,
                    'description': order['comment'],
                    "opencartid": order['order_id'],
                    "unicoding_integrations_id": self.id,
                    'order_ids': [(4, saleorder_id.id)],
                    'create_date': order['date_added'],
                })
            #except Exception as e:
            #    opencart_id.message_post(body=_('Failed to add order %s' % str(e)), subject=_('Opencart order import failed'))

        opencart_id.message_post(body=_('Added orders: %s' % str(orders_amount)), subject=_('OpenCart sync status'))





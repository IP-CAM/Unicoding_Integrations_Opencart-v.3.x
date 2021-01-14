<?php
class ControllerApiIntegrations extends Controller {

	public function orders() {
		$this->load->language('api/order');

		$this->load->model('account/integrations');


		$json = array();

		if(version_compare(VERSION, '3.0.0.0', '<') == true) {
			if (!isset($this->session->data['api_id']) && isset($this->session->session_id)) {
					$api = $this->model_account_integrations->getApiIdBySessionId($this->session->session_id, $this->request->get['api_token']);
					if(isset($api['api_id'])){
							$this->session->data['api_id'] = (int)$api['api_id'];
					}
			}
		}



		if (!isset($this->session->data['api_id'])) {
			$json['error'] = $this->language->get('error_permission');
		} else {
			$this->load->model('checkout/order');
			$this->load->model('account/order');
			$this->load->model('catalog/product');
			$this->load->model('catalog/category');



			$date = '';
			if (isset($this->request->get['date'])) {
				$date = $this->request->get['date'];
			}

			$limit = 10000;
			if (isset($this->request->get['limit'])) {
				$limit = $this->request->get['limit'];
			}

			$orders = $this->model_account_integrations->getOrdersOdoo($date, $limit);

			$json_orders = [];
			foreach($orders as $key=>$value){
				$json_orders[$value["order_id"]] = $this->model_account_integrations->getOrderOdoo($value["order_id"]);
				foreach($this->model_account_order->getOrderProducts($value["order_id"]) as $v1){

					$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]] = $v1;
					$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["options"] = $this->model_account_order->getOrderOptions($value["order_id"], $v1["order_product_id"]);
					$product_info = $this->model_catalog_product->getProduct($v1["product_id"]);

					if (isset($product_info["manufacturer"]))
						$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["manufacturer"] = $product_info["manufacturer"];
					else
						$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["manufacturer"] = "";


					$cat_ids = [];
					foreach($this->model_catalog_product->getCategories($v1["product_id"]) as $category){
						$cat_ids[] = $category["category_id"];
						break;
					}

					$category_id = max($cat_ids);
					if ($category_id){
						$category_info = $this->model_catalog_category->getCategory($category_id);
						$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["category"] = $category_info["name"];
					}else
						$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["category"] = "";



					$tax_rates = $this->tax->getRates($product_info['price'], $product_info['tax_class_id']);
					$json_orders[$value["order_id"]]["products"][$v1["order_product_id"]]["rates"] = $tax_rates;


				}
				$json_orders[$value["order_id"]]["totals"] = $this->model_account_order->getOrderTotals($value['order_id']);
				$json_orders[$value["order_id"]]["config_tax"] = $this->config->get('config_tax');
			}


			if ($orders) {
				$json['orders'] = $json_orders;

				$json['success'] = $this->language->get('text_success');
			} else {
				$json['error'] = $this->language->get('error_not_found');
			}
		}

		$this->response->addHeader('Content-Type: application/json');
		$this->response->setOutput(json_encode($json));
	}


}

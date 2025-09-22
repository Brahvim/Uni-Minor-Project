#include <stdio.h>
#include <esp_log.h>
#include <esp_wifi.h>
#include <esp_flash.h>
#include <nvs_flash.h>
#include <esp_camera.h>
#include <esp_http_client.h>

static char const *const s_tag = __FILE__;

sensor_t *g_sensor;
bool _Atomic g_transporting;
camera_config_t g_camera_config = {

	.pin_d0 = 5,
	.pin_d1 = 18,
	.pin_d2 = 19,
	.pin_d3 = 21,
	.pin_d4 = 36,
	.pin_d5 = 39,
	.pin_d6 = 34,
	.pin_d7 = 35,

	.pin_xclk = 0,
	.pin_pclk = 22,

	.pin_href = 23,
	.pin_pwdn = 32,
	.pin_reset = -1, // `-1` causes **software resets** only!
	.pin_vsync = 25,

	.pin_sccb_scl = 27, // Part of the SCCB DMA protocol...
	.pin_sccb_sda = 26, // Part of the SCCB DMA protocol...

	.xclk_freq_hz = 20000000, // 20M, i.e. 20MHz.
	.ledc_timer = LEDC_TIMER_0,
	.ledc_channel = LEDC_CHANNEL_0,

	.fb_count = 1,
	.jpeg_quality = 63,
	.frame_size = FRAMESIZE_VGA,
	.pixel_format = PIXFORMAT_JPEG, // `PIXFORMAT_JPEG` for streaming. `PIXFORMAT_RGB565` for face detection and recognition.
	.fb_location = CAMERA_FB_IN_PSRAM,
	.grab_mode = CAMERA_GRAB_WHEN_EMPTY,

};

void appCbckWifiDisconnected(void *p_args, esp_event_base_t p_base, int32_t p_evt, void *p_data) {
	if (likely(!g_transporting)) {

		esp_wifi_connect(); // To retry. Will probably lock this up and stuff.

	}
}

void appCbckWifiStart(void *p_args, esp_event_base_t p_base, int32_t p_evt, void *p_data) {
	esp_wifi_connect();
}

void appCbckIp(void *p_args, esp_event_base_t p_base, int32_t p_evt, void *p_data) {
	ip_event_got_ip_t const *const event = (ip_event_got_ip_t*) p_data;
	ESP_LOGI(s_tag, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
}

void app_main() {
	// Do camera things:
	ESP_ERROR_CHECK(esp_camera_init(&g_camera_config));
	g_sensor = esp_camera_sensor_get();

	// Apparently you need NVS for Wi-Fi:
	esp_err_t err_nvs = ESP_ERROR_CHECK_WITHOUT_ABORT(nvs_flash_init());
	if (unlikely(err_nvs == ESP_ERR_NVS_NO_FREE_PAGES || err_nvs == ESP_ERR_NVS_NEW_VERSION_FOUND)) {

		ESP_ERROR_CHECK(nvs_flash_erase());
		err_nvs = nvs_flash_init();

	}

	ESP_ERROR_CHECK(err_nvs);

	// Now we start Wi-Fi stations:
	ESP_ERROR_CHECK(esp_netif_init());
	ESP_ERROR_CHECK(esp_event_loop_create_default());
	esp_netif_create_default_wifi_sta();

	wifi_init_config_t const cfg = WIFI_INIT_CONFIG_DEFAULT();
	ESP_ERROR_CHECK(esp_wifi_init(&cfg));

	esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &appCbckIp, NULL, NULL);
	esp_event_handler_instance_register(WIFI_EVENT, WIFI_EVENT_STA_START, &appCbckWifiStart, NULL, NULL);
	esp_event_handler_instance_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, &appCbckWifiDisconnected, NULL, NULL);

	wifi_config_t wifi_config = {

		.sta = {

			.ssid = WIFI_SSID,
			.password = WIFI_PASS,
			.threshold.authmode = WIFI_AUTH_WPA2_PSK,

			.pmf_cfg = {

				.capable = true,
				.required = false,

			},

		},

	};

	ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
	ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
	// ESP_ERROR_CHECK(esp_wifi_start());

	esp_http_client_config_t const config = {

		.user_data = "",
		// .event_handler = NULL,
		.method = HTTP_METHOD_POST,
		// .auth_type = HTTP_AUTH_TYPE_BASIC,
		.url = "http://localhost:8080/",
		// .tls_version = ESP_HTTP_CLIENT_TLS_VER_TLS_1_3,

	};

	esp_http_client_handle_t client = esp_http_client_init(&config);
	esp_http_client_perform(client);
	esp_http_client_cleanup(client);
}

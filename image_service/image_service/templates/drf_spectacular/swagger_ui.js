const swaggerSettings = {{ settings|safe }};
const schemaAuthNames = {{ schema_auth_names|safe }};

{% if schema_auth_names %}
function schemaAuth(request) {
  let schemaAuthFailed = false;
  for (let i = 0; i < schemaAuthNames.length; i++) {
    const authName = schemaAuthNames[i];
    const authValue = localStorage.getItem(authName);
    if (authValue) {
      if (authName === 'csrfToken') {
        request.headers["X-CSRFTOKEN"] = authValue;
      } else {
        request.headers["Authorization"] = authValue;
      }
    } else {
      schemaAuthFailed = true;
    }
  }
  return request;
}
{% endif %}

const requestInterceptor = function(request) {
  {% if schema_auth_names %}
  request = schemaAuth(request);
  {% endif %}
  return request;
};

const responseInterceptor = function(response) {
  return response;
};

const plugins = [];

const ui = SwaggerUIBundle({
  url: "/api/schema/?format=json",
  dom_id: "#swagger-ui",
  presets: [SwaggerUIBundle.presets.apis],
  plugins,
  layout: "BaseLayout",
  requestInterceptor,
  responseInterceptor,
  ...swaggerSettings,
});

ui.initOAuth({});

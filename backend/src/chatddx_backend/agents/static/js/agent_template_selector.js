// src/chatddx_backend/agents/static/js/agent_template_selector.js
(function($) {
  $(document).ready(function() {
    const mapField = (id, value) => {
      const el = document.getElementById(id);
      if (el) { el.value = value; }
    };

    const mapSelect2Field = (id, value) => {
      const $el = $('#' + id);
      $el.val(value).trigger('change').trigger('select2:select');
    };

    const getData = (e) => {
      const templatesData = JSON.parse(e.target.getAttribute('data-templates'));
      return templatesData[e.target.value];
    };

    $('#id_template').on('select2:select', function(e) {
      data = getData(e);

      mapField('id_name', data.name);
      mapField('id_instructions', data.instructions || "");
      mapSelect2Field('id_connection_template', data.connection.id);
    });

    $('#id_connection_template').on('select2:select', function(e) {
      data = getData(e);

      mapField('id_connection_name', data.name);
      mapField('id_model', data.model);
      mapField('id_endpoint', data.endpoint);
      mapField('id_profile', data.profile_toml);
      mapSelect2Field('id_provider', data.provider);
    });
  });
})($)

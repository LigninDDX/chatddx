(function($) {
  $(document).ready(function() {
    const template_data = JSON.parse($('#template-data').html());
    const form_info = JSON.parse($('#form-info').html());

    const populateOptions = (model, data) => {
      const is_agent_plus = form_info.name === "agent_plus";
      const template_selector_id = is_agent_plus ? `#id_${model}_template` : '#id_template';
      const clear_id = `clear_${model}`;
      const $template_selector = $(template_selector_id);

      const populateField = (key, value) => {
        if (key.endsWith('_id')) {
          key = key.replace(/_id$/, '_template');
          value = String(value);
        }
        const field_id = (is_agent_plus && !key.endsWith('_template') ?
          `#id_${model}_${key}` : '#id_' + key
        );

        if (field_id === template_selector_id) return;

        const $field = $(field_id);
        if ($field.length) {
          let valueToSet = value;

          if (value === '' && $field.is('select')) {
            const targetModel = key.replace('_template', '');
            valueToSet = `clear_${targetModel}`;
          }

          $field.val(valueToSet);

          if ($field.is('select')) {
            $field.trigger('change');
          }
        }
      }

      $template_selector.empty().append($('<option>', { value: clear_id, text: "---------" }));

      $.each(data, function(model_id, option) {
        $template_selector.append($('<option>', { value: model_id, text: option.name }));
      });

      $template_selector.on('change', function() {
        const selected_id = $(this).val();

        if (selected_id === clear_id) {
          const fields = Object.keys(data)[0]; // boldly expect at least one row exists
          if (!fields) return;

          $.each(data[fields], function(key) {
            populateField(key, '');
          });
          return;
        }

        if (!selected_id) {
          console.warn(`no selected_id for model '${model}'`);
          return
        }
        if (!data[selected_id]) {
          console.warn(`no data for selected_id '${selected_id}'`);
          return;
        }

        $.each(data[selected_id], function(key, value) {
          populateField(key, value);
        });
      });

      const preselected_id = form_info[model];

      if (!preselected_id) {
        console.warn(`no preselected_id for model ${model}`);
      } else {
        $template_selector.val(preselected_id);
      }

    };

    if (form_info.name === "agent_plus") {
      $.each(template_data, function(model, data) {
        populateOptions(model, data);
      });
    } else {
      populateOptions(form_info.name, template_data[form_info.name]);
    }
  });
})(django.jQuery);

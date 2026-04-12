(function($) {
  $(document).ready(function() {
    const template_data = JSON.parse($('#template-data').html());

    const populateOptions = (model, data) => {
      const template_selector_id = "#id_" + model + "_template";
      const $template_selector = $(template_selector_id);

      $template_selector.on('change', function() {
        const selected_id = $(this).val();

        if (!selected_id) {
          console.log("no selection");
        };

        $.each(data[selected_id], function(key, value) {
          const field_id = '#id_' + model + "_" + key;

          if (field_id === template_selector_id) {
            return
          }

          const $field = $(field_id);

          if ($field.is('select')) {
            $field.val(value).trigger('change');
          } else {
            $field.val(value);
          }
        });
      });

      $.each(data, function(model_id, option) {
        $template_selector.append(
          $('<option>', {
            value: model_id,
            text: option.name,
          })
        );
      });
    };

    $.each(template_data, function(model, data) {
      populateOptions(model, data);
    });
  });
})($);

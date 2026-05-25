(function($) {
  $(document).ready(function() {
    const template_data = JSON.parse($('#template-data').html());
    const form_info = JSON.parse($('#form-info').html());

    const populateField = ($field, value) => {
      if ($field.length) {
        $field.val(value);

        if ($field.is('select')) {
          $field.trigger('change');
        }
      }
    }
    const attachTemplateSelector = (_, selector) => {
      const $target = $(selector.target);
      const target_data = template_data[selector.key];

      const get_field_id = (prefix, key) => `#id_${prefix}${key}`;

      $target.on('change', function() {
        const value = $(this).val();

        if (value === "") {
          const some_target = Object.keys(target_data)[0]; // boldly expect at least one row exists

          $.each(target_data[some_target], function(key) {
            const field_id = get_field_id(selector.field_prefix, key);
            if (field_id === selector.target) return;
            populateField($(field_id), '');
          });

          return;
        }

        $.each(target_data[value], function(key, value) {
          const field_id = get_field_id(selector.field_prefix, key)
          if (field_id === selector.target) return;
          console.log(field_id)
          populateField($(field_id), value);
        });

      });
    }

    $.each(form_info.template_selectors, attachTemplateSelector);
  });
})(django.jQuery);

(function($) {
  $(document).ready(function() {
    const registry = JSON.parse($('#template-data').html());
    const formInfo = JSON.parse($('#form-info').html());

    const populateField = ($field, value) => {
      if ($field.length) {
        $field.val(value);

        if ($field.is('select')) {
          $field.trigger('change');
        }
      }
    }
    const attachTemplateSelector = (_, selector) => {
      const selectorData = registry[selector.key];
      const maps = selector.maps || {}

      const getFieldId = (prefix, key) => `#id_${prefix || ""}${maps[key] || key}`;

      $(selector.target).on('change', function() {
        let clear = false;
        let choice = $(this).val();

        if (choice === "") {
          clear = true;
          choice = Object.keys(selectorData)[0]; // boldly expect at least one row exists
        }

        $.each(selectorData[choice] || {}, function(key, value) {
          const fieldId = getFieldId(selector.field_prefix, key);
          if (fieldId === selector.target) return;
          populateField($(fieldId), clear ? "" : value);
        });

      });
    }

    $.each(formInfo.template_selectors, attachTemplateSelector);
  });
})(django.jQuery);

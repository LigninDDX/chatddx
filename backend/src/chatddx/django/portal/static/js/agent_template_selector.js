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
      const fieldPrefix = selector.field_prefix || "";
      const maps = selector.maps || {};

      $(selector.target).on('change', function() {
        let choice = $(this).val();
        const clear = (choice === "");

        if (clear) {
          choice = Object.keys(selectorData)[0]; // boldly expect at least one row exists
        }

        $.each(selectorData[choice] || {}, function(key, value) {
          const fieldId = `#id_${fieldPrefix}${maps[key] || key}`;
          if (fieldId === selector.target) return;
          populateField($(fieldId), clear ? "" : value);
        });

      });
    }

    $.each(formInfo.template_selectors, attachTemplateSelector);
  });
})(django.jQuery);

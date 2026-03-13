$(function () {
    const original_col_1 = render.col_1;
    render.col_1 = function (data, type, full, meta) {
        if (type === "display" && full._meta && full._meta.can_edit === false) {
            const $actions = $("<div>").html(full._meta.rowActions);
            $actions.find('[data-name="edit"], [data-name="delete"]').remove();
            return `<div class="row-actions-container" data-id="${data}">${$actions.html()}</div>`;
        }
        return original_col_1(data, type, full, meta);
    };
});

Object.assign(render, {
    spatial_extent_render_key: function render(data, type, full, meta, fieldOptions) {
        if (type !== "display") return escape(JSON.stringify(data));
        if (data) {
            // return `<span class="align-middle d-inline-block text-truncate" data-toggle="tooltip" data-placement="bottom" title='${escape(
            //     JSON.stringify(data)
            // )}' style="max-width: 30em;">${pretty_print_json(data)}</span>`;
            return `<span class="align-middle d-inline-block text-truncate" data-toggle="tooltip" data-placement="bottom" title='${escape(
                JSON.stringify(data)
            )}' style="max-width: 30em;">(${data['min-lon']}, ${data['min-lat']}), (${data['max-lon']}, ${data['max-lat']})</span>`;
        } else return null_column();
    },
});
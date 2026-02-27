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
utils = {};
utils.datatables =  {};
utils.datatables.defaults = {
            "processing": true,
            "responsive": true,
            "lengthMenu": [[10, 25, 50, -1], [10, 25, 50, "All"]],
            "language": {
                "paginate": {
                    "next": "Volgende",
                    "previous": "Vorige"
                }
            },
            "columnDefs": [ {
                "targets": [0],
                "visible": false,
                "searchable": false
            }],
};

utils.datatables.enable_select = function ($selector) {
    $selector.on( 'click', 'tr', function () {
        $(this).toggleClass('info');
    } );
};

utils.datatables.get_ids = function($selector, table) {
    var selected_ids = [];
    var selected_users = "";
    var selected_rows = table.rows('.info');
    for (i = 0; i < selected_rows.data().length; i++) {
        selected_ids.push(selected_rows.data()[i][0]);
        selected_users += "- " + selected_rows.data()[i][1] + "\n";
    }
    return { "selected_ids" : selected_ids };
}

utils.datatables.action_by_url = function(
    $selector, table, url, action, refer) {
    $selector.click(function () {
        var json_data = utils.datatables.get_ids($selector, table);
        if (confirm('Are you sure you want to ' + action + '?\n')) {
            $.ajax({
                type: action,
                url: url,
                contentType: 'application/json',
                success: function (data) {
                    if (action === "put") {
                        window.open(refer, "_top");
                    } else {
                        table.ajax.reload();
                    }
                },
                data: JSON.stringify(json_data, null, '\t'),
            });
        } else {
            return;
        }
    });
};
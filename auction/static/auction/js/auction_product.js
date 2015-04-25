function commafy( num ) {
    var str = num.toString().split('.');
    if (str[0].length >= 5) {
        str[0] = str[0].replace(/(\d)(?=(\d{3})+$)/g, '$1,');
    }
    if (str[1] && str[1].length >= 5) {
        str[1] = str[1].replace(/(\d{3})/g, '$1 ');
    }
    return str.join('.');
}

window.setInterval(function () {

    id = document.getElementById("itemid").value;

    $.ajax({
        url: "/updateBid",
        data: {
            itemid : id,
        },
        dataType : "json",
        success: function( bidInfo ) {
            if (bidInfo === 'Malicious HTTP Request')
            {
                $("message").empty();
                $("message").append(bidInfo);
            }
            else
            {
                $("#bidValue").empty()
                $("#bidValue").prepend("<a href = \"/bid/" + String(id) + "\" class=\"btn btn-primary btn-sg\">Bid Starting At $" +
                commafy(bidInfo.bidPrice) +"</a>");
            }

        },
        error: function(){
            $("#message").empty();
            $("#message").append("AJAX Error");
        }
    });
}, 5000);
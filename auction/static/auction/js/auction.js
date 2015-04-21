var req;

//ask if this will be called even when not on the page
window.setInterval(function () {

    id = document.getElementById("itemid").value;

    $.ajax({
        url: "/update_bid",
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
                $("#bidValue").prepend("<a href = \"/bid/" + String(id) + "\" class=\"btn btn-primary btn-sg\">Bid Starting At $"+ bidInfo.bidPrice +"</a> ");
            }

        },
        error: function(){
            $("message").empty();
            $("message").append("AJAX Error");
        }
    });
}, 5000);






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
                $("#message").empty();
                $("#message").append(bidInfo);
            }
            else
            {
                $("#bidValue").empty();
                $("#bidValue").prepend('$' + bidInfo.bidPrice);
                $("#bidMessage").empty();
                $("#bidMessage").prepend(bidInfo.message);
                $('#message').empty();
                $('#message').prepend('You must bid more than $' + bidInfo.bidPrice);
            }

        },
        error: function(){
            $("#message").empty();
            $("#message").append("AJAX Error");
        }
    });
}, 5000);

function bidA()
{
    //Get bid value out of form
    var bidAmount = $('#id_bid')[0].value;
    $('#id_bid')[0].value = "";
    bidAmount = parseFloat(bidAmount);
    var currentBid = $('#bidValue')[0].innerHTML;
    currentBid = parseFloat(currentBid.substring(1));
    var id = document.getElementById("itemid").value;

    if (bidAmount < currentBid)
    {
        $('#message').empty();
        $('#message').prepend('You must bid more than $' + currentBid);
    }
    else
    {
        var csrfToken = document.getElementsByTagName("input")[2].value;
        $.ajax({
        url: "/submitBid",
        data: {
            'itemid' : id,
            'bidAmount' : bidAmount,
            'csrfmiddlewaretoken': csrfToken
        },

        dataType : "json",

        type: "POST",

        success: function( bidInfo ) {
            if (bidInfo === 'Malicious HTTP Request')
            {
                $("#message").empty();
                $("#message").append(bidInfo);
            }
            else
            {
                $("#bidValue").empty();
                $("#bidValue").prepend('$' + parseFloat(bidInfo.bidPrice).toFixed(2));
                $("#bidMessage").empty();
                $("#bidMessage").prepend(bidInfo.message);
                $('#message').empty();
                $('#message').prepend('You must bid more than $' + parseFloat(bidInfo.bidPrice).toFixed(2));
                $('#id_bid').empty();
            }

        },
        error: function(){
            $("#message").empty();
            $("#message").append("AJAX Error");
        }
    });
    }
}
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

function deleteCommas(str)
{
    return str.replace(/,/g , "");
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
                $("#message").empty();
                $("#message").append(bidInfo);
            }
            else
            {
                $("#bidValue").empty();
                $("#bidValue").prepend('$' + commafy(bidInfo.bidPrice));
                $("#bidMessage").empty();
                $("#bidMessage").prepend(bidInfo.message);
                $('#message').empty();
                $('#message').prepend('You must bid more than $' + commafy(bidInfo.bidPrice));
            }

        },
        error: function(){
            $("#message").empty();
            $("#message").append("AJAX Error");
        }
    });
}, 2000);

function bid()
{
    //Get bid value out of form
    var bidAmount = $('#id_bid')[0].value;
    if (bidAmount != parseFloat(bidAmount))
    {
        $('#message').empty();
        $('#message').append(' Please type a number for your bid');
        $('#id_bid')[0].value = "";
        return;
    }

    bidAmount = parseFloat(bidAmount);
    var currentBid = $('#bidValue')[0].innerHTML;
    currentBid = parseFloat(deleteCommas(currentBid.substring(1)));
    var id = document.getElementById("itemid").value;
    $('#id_bid')[0].value = "";
    if (bidAmount < currentBid)
    {
        $('#message').empty();
        $('#message').prepend('You must bid more than $' + commafy(currentBid.toFixed(2)));
    }
    else if (bidAmount > 99999999.99)
    {
        $('#message').empty();
        $('#message').prepend('You cannot bid more than $' + commafy(99999999.99));
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
            else if (bidInfo === 'Item has been sold')
            {
                $("#message").empty();
                $("#message").append(bidInfo);
            }
            else
            {
                $("#bidValue").empty();
                if (bidInfo.bidPrice == parseFloat(bidInfo.bidPrice))
                {
                    $("#bidValue").prepend('$' + commafy(parseFloat(bidInfo.bidPrice).toFixed(2)));
                    $("#bidMessage").empty();
                    $("#bidMessage").prepend(bidInfo.message);
                    $('#message').empty();
                    $('#message').prepend('You must bid more than $' + commafy(parseFloat(bidInfo.bidPrice).toFixed(2)));
                    $('#id_bid').empty();    
                }
                else
                {
                    //error handling
                    $("#message").empty();
                    $("#message").append("AJAX Error");
                }
                
            }

        },
        error: function() {
            $("#message").empty();
            $("#message").append("AJAX Error");
        }
    });
    }
}
function rate(numStars, itemId)
{
    var csrfToken = document.getElementsByTagName("input")[3].value;
	//Send AJAX request to back end
	$.ajax({
        url: "/rate",
        data: {
            'numStars' : numStars,
            'id' : itemId,
            'csrfmiddlewaretoken': csrfToken
        },

        dataType : "json",

        type: "POST",

        success: function( newRating ) {
            if (newRating === parseFloat(newRating))
            {
        	   $("#rating").empty();
        	   for (var i = 0; i < Math.floor(newRating); i++)
        	   {
            		$("#rating").prepend("<span class=\"glyphicon glyphicon-star\"></span> ");
        	   }
                for (var i = Math.floor(newRating); i < 5; i++)
                {
                    $("#rating").append("<span class=\"glyphicon glyphicon-star-empty\"></span> ");
                }
        	   $("#rating").append(" " + newRating.toFixed(2) + " stars");
            }
            else
            {
                $("#error").empty();
                $("#error").append(newRating);
            }

        },

        error: function(){
            $("#error").empty();
            $("#error").append('AJAX failed');
        }
    });
}
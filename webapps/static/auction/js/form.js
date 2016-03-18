function loadMoreOptions()
{
	var choice = document.getElementById("id_sellingChoice").value;
	var head1 = document.getElementById("1head");
	var box1 = document.getElementById("1box");
	var head2 = document.getElementById("2head");
	var box2 = document.getElementById("2box");
	var head3 = document.getElementById("3head");
	var box3 = document.getElementById("3box");
	head1.innerHTML = ""
	box1.innerHTML = ""
	head2.innerHTML = ""
	box2.innerHTML = ""
	head3.innerHTML = ""
	box3.innerHTML = ""
	if (choice === "BUY")
	{
		head1.innerHTML = "<label for=\"id_price\">Price:</label>";
		box1.innerHTML = "<input id=\"id_price\" name=\"price\" step=\"0.01\" type=\"number\" /></td></tr>";
	}
	else if (choice === "BID")
	{
		head1.innerHTML = "<label for=\"id_bidPrice\">Bid Price:</label>";
		box1.innerHTML = "<input id=\"id_bidPrice\" name=\"bidPrice\" step=\"0.01\" type=\"number\" /></td></tr>";
		head2.innerHTML = "<label for=\"id_endBidDate\">End Bid Date:</label>";
		box2.innerHTML = "<input id=\"id_endBidDate\" name=\"endBidDate\" type=\"date\" /></td></tr>";
	}
	else if (choice === "BIDBUY")
	{
		head1.innerHTML = "<label for=\"id_price\">Price:</label>";
		box1.innerHTML = "<input id=\"id_price\" name=\"price\" step=\"0.01\" type=\"number\" /></td></tr>";
		head2.innerHTML = "<label for=\"id_bidPrice\">Bid Price:</label>";
		box2.innerHTML = "<input id=\"id_bidPrice\" name=\"bidPrice\" step=\"0.01\" type=\"number\" /></td></tr>";
		head3.innerHTML = "<label for=\"id_endBidDate\">End Bid Date:</label>";
		box3.innerHTML = "<input id=\"id_endBidDate\" name=\"endBidDate\" type=\"date\" /></td></tr>";
	}
	else
	{
		//error handling. Should never reach here
		$("#error").empty();
		$("#error").append("Error");
	}
}
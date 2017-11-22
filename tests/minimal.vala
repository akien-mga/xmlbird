using B;

public static int main (string[] arg) {
	B.Test t;
	
	t = new B.Test ("""<test1><inside attr="a" /></test1>""");
	t.test ("test1 inside attr a");

	t = new B.Test ("""<nesting><nested><nested><inside/></nested></nested></nesting>""");
	t.test ("nesting nested nested inside");

	t = new B.Test ("""<a><!-- Comment --><b /></a>""");
	t.test ("a b");

	t = new B.Test ("""<root><quote>"<a attr="b" />"</quote></root>""");
	t.test ("root quote a attr b");

	t = new B.Test ("""<single/>""");
	t.test ("single");

	t = new B.Test ("""<single_space />""");
	t.test ("single_space");
	
	string needs_encoding = "\"'<>&";
	string encoded = XmlParser.encode (needs_encoding);
	string decoded = XmlParser.decode (encoded);

	if (needs_encoding != decoded) {
		print (@"Xml encoding failed:$encoded\n");
		print (@"Xml encoding failed:$needs_encoding != $decoded\n");
		assert (false);
	} else {
		print (@"Xml encoding passed: $needs_encoding == $decoded\n");
	}
	
	XmlParser parser = new XmlParser ("<tag1><tag1><tag2/></tag1>");
	assert (!parser.validate ());

	return 0;
}

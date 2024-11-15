local export = {}

local collation_module = "collation/collation.lua"
local languages_module = "languages.lua"
local maintenance_category_module = "Module:maintenance category"
local string_utilities_module = "Module:string utilities"
local table_module = "table.lua"
local template_parser_module = "Module:template parser"

local mw = mw
local string = string
local table = table
local ustring = mw.ustring

local concat = table.concat
local find = string.find
local insert = table.insert
local load_data = mw.loadData
local match = string.match
local new_title = mw.title.new
local pairs = pairs
local require = require
local sub = string.sub
local toNFC = ustring.toNFC
local toNFD = ustring.toNFD
local ugsub = ustring.gsub

local langnames = load_data("Module:languages/canonical names")

-- Functions in other modules that load locally on demand by dereferencing themselves.
local function class_else_type(...)
	class_else_type = require(template_parser_module).class_else_type
	return class_else_type(...)
end

local function decode_entities(...)
	decode_entities = require(string_utilities_module).decode_entities
	return decode_entities(...)
end

local function encode_entities(...)
	encode_entities = require(string_utilities_module).encode_entities
	return encode_entities(...)
end

local function get_category(...)
	get_category = require(maintenance_category_module).get_category
	return get_category(...)
end

local function get_lang(...)
	get_lang = require(languages_module).getByCode
	return get_lang(...)
end

local function list_to_set(...)
	list_to_set = require(table_module).listToSet
	return list_to_set(...)
end

local function parse(...)
	parse = require(template_parser_module).parse
	return parse(...)
end

local function remove_comments(...)
	remove_comments = require(string_utilities_module).remove_comments
	return remove_comments(...)
end

local function split(...)
	split = require(string_utilities_module).split
	return split(...)
end

local function string_sort(...)
	string_sort = require(collation_module).string_sort
	return string_sort(...)
end

local function u(...)
	u = require(string_utilities_module).char
	return u(...)
end

local function uupper(...)
	uupper = require(string_utilities_module).upper
	return uupper(...)
end

-- Combining character data used when categorising unusual characters. These resolve into two patterns, used to find
-- single combining characters (i.e. character + diacritic(s)) or double combining characters (i.e. character +
-- diacritic(s) + character).
-- Charsets are in the format used by Unicode's UnicodeSet tool: https://util.unicode.org/UnicodeJsps/list-unicodeset.jsp.

-- Single combining characters.
-- Charset: [[:M:]&[:^Canonical_Combining_Class=/^Double_/:]&[:^subhead=Grapheme joiner:]&[:^Variation_Selector=Yes:]]
-- Note: concatenating hundreds of lines at once gives an error, so () are used every 150 lines to break it up into chunks.
local comb_chars_single =
	("\204\128-\205\142" .. -- U+0300-U+034E
	"\205\144-\205\155" .. -- U+0350-U+035B
	"\205\163-\205\175" .. -- U+0363-U+036F
	"\210\131-\210\137" .. -- U+0483-U+0489
	"\214\145-\214\189" .. -- U+0591-U+05BD
	"\214\191" .. -- U+05BF
	"\215\129" .. -- U+05C1
	"\215\130" .. -- U+05C2
	"\215\132" .. -- U+05C4
	"\215\133" .. -- U+05C5
	"\215\135" .. -- U+05C7
	"\216\144-\216\154" .. -- U+0610-U+061A
	"\217\139-\217\159" .. -- U+064B-U+065F
	"\217\176" .. -- U+0670
	"\219\150-\219\156" .. -- U+06D6-U+06DC
	"\219\159-\219\164" .. -- U+06DF-U+06E4
	"\219\167" .. -- U+06E7
	"\219\168" .. -- U+06E8
	"\219\170-\219\173" .. -- U+06EA-U+06ED
	"\220\145" .. -- U+0711
	"\220\176-\221\138" .. -- U+0730-U+074A
	"\222\166-\222\176" .. -- U+07A6-U+07B0
	"\223\171-\223\179" .. -- U+07EB-U+07F3
	"\223\189" .. -- U+07FD
	"\224\160\150-\224\160\153" .. -- U+0816-U+0819
	"\224\160\155-\224\160\163" .. -- U+081B-U+0823
	"\224\160\165-\224\160\167" .. -- U+0825-U+0827
	"\224\160\169-\224\160\173" .. -- U+0829-U+082D
	"\224\161\153-\224\161\155" .. -- U+0859-U+085B
	"\224\162\151-\224\162\159" .. -- U+0897-U+089F
	"\224\163\138-\224\163\161" .. -- U+08CA-U+08E1
	"\224\163\163-\224\164\131" .. -- U+08E3-U+0903
	"\224\164\186-\224\164\188" .. -- U+093A-U+093C
	"\224\164\190-\224\165\143" .. -- U+093E-U+094F
	"\224\165\145-\224\165\151" .. -- U+0951-U+0957
	"\224\165\162" .. -- U+0962
	"\224\165\163" .. -- U+0963
	"\224\166\129-\224\166\131" .. -- U+0981-U+0983
	"\224\166\188" .. -- U+09BC
	"\224\166\190-\224\167\132" .. -- U+09BE-U+09C4
	"\224\167\135" .. -- U+09C7
	"\224\167\136" .. -- U+09C8
	"\224\167\139-\224\167\141" .. -- U+09CB-U+09CD
	"\224\167\151" .. -- U+09D7
	"\224\167\162" .. -- U+09E2
	"\224\167\163" .. -- U+09E3
	"\224\167\190" .. -- U+09FE
	"\224\168\129-\224\168\131" .. -- U+0A01-U+0A03
	"\224\168\188" .. -- U+0A3C
	"\224\168\190-\224\169\130" .. -- U+0A3E-U+0A42
	"\224\169\135" .. -- U+0A47
	"\224\169\136" .. -- U+0A48
	"\224\169\139-\224\169\141" .. -- U+0A4B-U+0A4D
	"\224\169\145" .. -- U+0A51
	"\224\169\176" .. -- U+0A70
	"\224\169\177" .. -- U+0A71
	"\224\169\181" .. -- U+0A75
	"\224\170\129-\224\170\131" .. -- U+0A81-U+0A83
	"\224\170\188" .. -- U+0ABC
	"\224\170\190-\224\171\133" .. -- U+0ABE-U+0AC5
	"\224\171\135-\224\171\137" .. -- U+0AC7-U+0AC9
	"\224\171\139-\224\171\141" .. -- U+0ACB-U+0ACD
	"\224\171\162" .. -- U+0AE2
	"\224\171\163" .. -- U+0AE3
	"\224\171\186-\224\171\191" .. -- U+0AFA-U+0AFF
	"\224\172\129-\224\172\131" .. -- U+0B01-U+0B03
	"\224\172\188" .. -- U+0B3C
	"\224\172\190-\224\173\132" .. -- U+0B3E-U+0B44
	"\224\173\135" .. -- U+0B47
	"\224\173\136" .. -- U+0B48
	"\224\173\139-\224\173\141" .. -- U+0B4B-U+0B4D
	"\224\173\149-\224\173\151" .. -- U+0B55-U+0B57
	"\224\173\162" .. -- U+0B62
	"\224\173\163" .. -- U+0B63
	"\224\174\130" .. -- U+0B82
	"\224\174\190-\224\175\130" .. -- U+0BBE-U+0BC2
	"\224\175\134-\224\175\136" .. -- U+0BC6-U+0BC8
	"\224\175\138-\224\175\141" .. -- U+0BCA-U+0BCD
	"\224\175\151" .. -- U+0BD7
	"\224\176\128-\224\176\132" .. -- U+0C00-U+0C04
	"\224\176\188" .. -- U+0C3C
	"\224\176\190-\224\177\132" .. -- U+0C3E-U+0C44
	"\224\177\134-\224\177\136" .. -- U+0C46-U+0C48
	"\224\177\138-\224\177\141" .. -- U+0C4A-U+0C4D
	"\224\177\149" .. -- U+0C55
	"\224\177\150" .. -- U+0C56
	"\224\177\162" .. -- U+0C62
	"\224\177\163" .. -- U+0C63
	"\224\178\129-\224\178\131" .. -- U+0C81-U+0C83
	"\224\178\188" .. -- U+0CBC
	"\224\178\190-\224\179\132" .. -- U+0CBE-U+0CC4
	"\224\179\134-\224\179\136" .. -- U+0CC6-U+0CC8
	"\224\179\138-\224\179\141" .. -- U+0CCA-U+0CCD
	"\224\179\149" .. -- U+0CD5
	"\224\179\150" .. -- U+0CD6
	"\224\179\162" .. -- U+0CE2
	"\224\179\163" .. -- U+0CE3
	"\224\179\179" .. -- U+0CF3
	"\224\180\128-\224\180\131" .. -- U+0D00-U+0D03
	"\224\180\187" .. -- U+0D3B
	"\224\180\188" .. -- U+0D3C
	"\224\180\190-\224\181\132" .. -- U+0D3E-U+0D44
	"\224\181\134-\224\181\136" .. -- U+0D46-U+0D48
	"\224\181\138-\224\181\141" .. -- U+0D4A-U+0D4D
	"\224\181\151" .. -- U+0D57
	"\224\181\162" .. -- U+0D62
	"\224\181\163" .. -- U+0D63
	"\224\182\129-\224\182\131" .. -- U+0D81-U+0D83
	"\224\183\138" .. -- U+0DCA
	"\224\183\143-\224\183\148" .. -- U+0DCF-U+0DD4
	"\224\183\150" .. -- U+0DD6
	"\224\183\152-\224\183\159" .. -- U+0DD8-U+0DDF
	"\224\183\178" .. -- U+0DF2
	"\224\183\179" .. -- U+0DF3
	"\224\184\177" .. -- U+0E31
	"\224\184\180-\224\184\186" .. -- U+0E34-U+0E3A
	"\224\185\135-\224\185\142" .. -- U+0E47-U+0E4E
	"\224\186\177" .. -- U+0EB1
	"\224\186\180-\224\186\188" .. -- U+0EB4-U+0EBC
	"\224\187\136-\224\187\142" .. -- U+0EC8-U+0ECE
	"\224\188\152" .. -- U+0F18
	"\224\188\153" .. -- U+0F19
	"\224\188\181" .. -- U+0F35
	"\224\188\183" .. -- U+0F37
	"\224\188\185" .. -- U+0F39
	"\224\188\190" .. -- U+0F3E
	"\224\188\191" .. -- U+0F3F
	"\224\189\177-\224\190\132" .. -- U+0F71-U+0F84
	"\224\190\134" .. -- U+0F86
	"\224\190\135" .. -- U+0F87
	"\224\190\141-\224\190\151" .. -- U+0F8D-U+0F97
	"\224\190\153-\224\190\188" .. -- U+0F99-U+0FBC
	"\224\191\134" .. -- U+0FC6
	"\225\128\171-\225\128\190" .. -- U+102B-U+103E
	"\225\129\150-\225\129\153" .. -- U+1056-U+1059
	"\225\129\158-\225\129\160" .. -- U+105E-U+1060
	"\225\129\162-\225\129\164" .. -- U+1062-U+1064
	"\225\129\167-\225\129\173" .. -- U+1067-U+106D
	"\225\129\177-\225\129\180" .. -- U+1071-U+1074
	"\225\130\130-\225\130\141" .. -- U+1082-U+108D
	"\225\130\143" .. -- U+108F
	"\225\130\154-\225\130\157" .. -- U+109A-U+109D
	"\225\141\157-\225\141\159" .. -- U+135D-U+135F
	"\225\156\146-\225\156\149" .. -- U+1712-U+1715
	"\225\156\178-\225\156\180" .. -- U+1732-U+1734
	"\225\157\146" .. -- U+1752
	"\225\157\147" .. -- U+1753
	"\225\157\178" .. -- U+1772
	"\225\157\179" .. -- U+1773
	"\225\158\180-\225\159\147") .. -- U+17B4-U+17D3
	("\225\159\157" .. -- U+17DD
	"\225\162\133" .. -- U+1885
	"\225\162\134" .. -- U+1886
	"\225\162\169" .. -- U+18A9
	"\225\164\160-\225\164\171" .. -- U+1920-U+192B
	"\225\164\176-\225\164\187" .. -- U+1930-U+193B
	"\225\168\151-\225\168\155" .. -- U+1A17-U+1A1B
	"\225\169\149-\225\169\158" .. -- U+1A55-U+1A5E
	"\225\169\160-\225\169\188" .. -- U+1A60-U+1A7C
	"\225\169\191" .. -- U+1A7F
	"\225\170\176-\225\171\142" .. -- U+1AB0-U+1ACE
	"\225\172\128-\225\172\132" .. -- U+1B00-U+1B04
	"\225\172\180-\225\173\132" .. -- U+1B34-U+1B44
	"\225\173\171-\225\173\179" .. -- U+1B6B-U+1B73
	"\225\174\128-\225\174\130" .. -- U+1B80-U+1B82
	"\225\174\161-\225\174\173" .. -- U+1BA1-U+1BAD
	"\225\175\166-\225\175\179" .. -- U+1BE6-U+1BF3
	"\225\176\164-\225\176\183" .. -- U+1C24-U+1C37
	"\225\179\144-\225\179\146" .. -- U+1CD0-U+1CD2
	"\225\179\148-\225\179\168" .. -- U+1CD4-U+1CE8
	"\225\179\173" .. -- U+1CED
	"\225\179\180" .. -- U+1CF4
	"\225\179\183-\225\179\185" .. -- U+1CF7-U+1CF9
	"\225\183\128-\225\183\140" .. -- U+1DC0-U+1DCC
	"\225\183\142-\225\183\187" .. -- U+1DCE-U+1DFB
	"\225\183\189-\225\183\191" .. -- U+1DFD-U+1DFF
	"\226\131\144-\226\131\176" .. -- U+20D0-U+20F0
	"\226\179\175-\226\179\177" .. -- U+2CEF-U+2CF1
	"\226\181\191" .. -- U+2D7F
	"\226\183\160-\226\183\191" .. -- U+2DE0-U+2DFF
	"\227\128\170-\227\128\175" .. -- U+302A-U+302F
	"\227\130\153" .. -- U+3099
	"\227\130\154" .. -- U+309A
	"\234\153\175-\234\153\178" .. -- U+A66F-U+A672
	"\234\153\180-\234\153\189" .. -- U+A674-U+A67D
	"\234\154\158" .. -- U+A69E
	"\234\154\159" .. -- U+A69F
	"\234\155\176" .. -- U+A6F0
	"\234\155\177" .. -- U+A6F1
	"\234\160\130" .. -- U+A802
	"\234\160\134" .. -- U+A806
	"\234\160\139" .. -- U+A80B
	"\234\160\163-\234\160\167" .. -- U+A823-U+A827
	"\234\160\172" .. -- U+A82C
	"\234\162\128" .. -- U+A880
	"\234\162\129" .. -- U+A881
	"\234\162\180-\234\163\133" .. -- U+A8B4-U+A8C5
	"\234\163\160-\234\163\177" .. -- U+A8E0-U+A8F1
	"\234\163\191" .. -- U+A8FF
	"\234\164\166-\234\164\173" .. -- U+A926-U+A92D
	"\234\165\135-\234\165\147" .. -- U+A947-U+A953
	"\234\166\128-\234\166\131" .. -- U+A980-U+A983
	"\234\166\179-\234\167\128" .. -- U+A9B3-U+A9C0
	"\234\167\165" .. -- U+A9E5
	"\234\168\169-\234\168\182" .. -- U+AA29-U+AA36
	"\234\169\131" .. -- U+AA43
	"\234\169\140" .. -- U+AA4C
	"\234\169\141" .. -- U+AA4D
	"\234\169\187-\234\169\189" .. -- U+AA7B-U+AA7D
	"\234\170\176" .. -- U+AAB0
	"\234\170\178-\234\170\180" .. -- U+AAB2-U+AAB4
	"\234\170\183" .. -- U+AAB7
	"\234\170\184" .. -- U+AAB8
	"\234\170\190" .. -- U+AABE
	"\234\170\191" .. -- U+AABF
	"\234\171\129" .. -- U+AAC1
	"\234\171\171-\234\171\175" .. -- U+AAEB-U+AAEF
	"\234\171\181" .. -- U+AAF5
	"\234\171\182" .. -- U+AAF6
	"\234\175\163-\234\175\170" .. -- U+ABE3-U+ABEA
	"\234\175\172" .. -- U+ABEC
	"\234\175\173" .. -- U+ABED
	"\239\172\158" .. -- U+FB1E
	"\239\184\160-\239\184\175" .. -- U+FE20-U+FE2F
	"\240\144\135\189" .. -- U+101FD
	"\240\144\139\160" .. -- U+102E0
	"\240\144\141\182-\240\144\141\186" .. -- U+10376-U+1037A
	"\240\144\168\129-\240\144\168\131" .. -- U+10A01-U+10A03
	"\240\144\168\133" .. -- U+10A05
	"\240\144\168\134" .. -- U+10A06
	"\240\144\168\140-\240\144\168\143" .. -- U+10A0C-U+10A0F
	"\240\144\168\184-\240\144\168\186" .. -- U+10A38-U+10A3A
	"\240\144\168\191" .. -- U+10A3F
	"\240\144\171\165" .. -- U+10AE5
	"\240\144\171\166" .. -- U+10AE6
	"\240\144\180\164-\240\144\180\167" .. -- U+10D24-U+10D27
	"\240\144\181\169-\240\144\181\173" .. -- U+10D69-U+10D6D
	"\240\144\186\171" .. -- U+10EAB
	"\240\144\186\172" .. -- U+10EAC
	"\240\144\187\188-\240\144\187\191" .. -- U+10EFC-U+10EFF
	"\240\144\189\134-\240\144\189\144" .. -- U+10F46-U+10F50
	"\240\144\190\130-\240\144\190\133" .. -- U+10F82-U+10F85
	"\240\145\128\128-\240\145\128\130" .. -- U+11000-U+11002
	"\240\145\128\184-\240\145\129\134" .. -- U+11038-U+11046
	"\240\145\129\176" .. -- U+11070
	"\240\145\129\179" .. -- U+11073
	"\240\145\129\180" .. -- U+11074
	"\240\145\129\191-\240\145\130\130" .. -- U+1107F-U+11082
	"\240\145\130\176-\240\145\130\186" .. -- U+110B0-U+110BA
	"\240\145\131\130" .. -- U+110C2
	"\240\145\132\128-\240\145\132\130" .. -- U+11100-U+11102
	"\240\145\132\167-\240\145\132\180" .. -- U+11127-U+11134
	"\240\145\133\133" .. -- U+11145
	"\240\145\133\134" .. -- U+11146
	"\240\145\133\179" .. -- U+11173
	"\240\145\134\128-\240\145\134\130" .. -- U+11180-U+11182
	"\240\145\134\179-\240\145\135\128" .. -- U+111B3-U+111C0
	"\240\145\135\137-\240\145\135\140" .. -- U+111C9-U+111CC
	"\240\145\135\142" .. -- U+111CE
	"\240\145\135\143" .. -- U+111CF
	"\240\145\136\172-\240\145\136\183" .. -- U+1122C-U+11237
	"\240\145\136\190" .. -- U+1123E
	"\240\145\137\129" .. -- U+11241
	"\240\145\139\159-\240\145\139\170" .. -- U+112DF-U+112EA
	"\240\145\140\128-\240\145\140\131" .. -- U+11300-U+11303
	"\240\145\140\187" .. -- U+1133B
	"\240\145\140\188" .. -- U+1133C
	"\240\145\140\190-\240\145\141\132" .. -- U+1133E-U+11344
	"\240\145\141\135" .. -- U+11347
	"\240\145\141\136" .. -- U+11348
	"\240\145\141\139-\240\145\141\141" .. -- U+1134B-U+1134D
	"\240\145\141\151" .. -- U+11357
	"\240\145\141\162" .. -- U+11362
	"\240\145\141\163" .. -- U+11363
	"\240\145\141\166-\240\145\141\172" .. -- U+11366-U+1136C
	"\240\145\141\176-\240\145\141\180" .. -- U+11370-U+11374
	"\240\145\142\184-\240\145\143\128" .. -- U+113B8-U+113C0
	"\240\145\143\130" .. -- U+113C2
	"\240\145\143\133" .. -- U+113C5
	"\240\145\143\135-\240\145\143\138" .. -- U+113C7-U+113CA
	"\240\145\143\140-\240\145\143\144" .. -- U+113CC-U+113D0
	"\240\145\143\146" .. -- U+113D2
	"\240\145\143\161" .. -- U+113E1
	"\240\145\143\162" .. -- U+113E2
	"\240\145\144\181-\240\145\145\134" .. -- U+11435-U+11446
	"\240\145\145\158" .. -- U+1145E
	"\240\145\146\176-\240\145\147\131" .. -- U+114B0-U+114C3
	"\240\145\150\175-\240\145\150\181" .. -- U+115AF-U+115B5
	"\240\145\150\184-\240\145\151\128" .. -- U+115B8-U+115C0
	"\240\145\151\156" .. -- U+115DC
	"\240\145\151\157" .. -- U+115DD
	"\240\145\152\176-\240\145\153\128" .. -- U+11630-U+11640
	"\240\145\154\171-\240\145\154\183" .. -- U+116AB-U+116B7
	"\240\145\156\157-\240\145\156\171" .. -- U+1171D-U+1172B
	"\240\145\160\172-\240\145\160\186" .. -- U+1182C-U+1183A
	"\240\145\164\176-\240\145\164\181" .. -- U+11930-U+11935
	"\240\145\164\183" .. -- U+11937
	"\240\145\164\184" .. -- U+11938
	"\240\145\164\187-\240\145\164\190" .. -- U+1193B-U+1193E
	"\240\145\165\128") .. -- U+11940
	("\240\145\165\130" .. -- U+11942
	"\240\145\165\131" .. -- U+11943
	"\240\145\167\145-\240\145\167\151" .. -- U+119D1-U+119D7
	"\240\145\167\154-\240\145\167\160" .. -- U+119DA-U+119E0
	"\240\145\167\164" .. -- U+119E4
	"\240\145\168\129-\240\145\168\138" .. -- U+11A01-U+11A0A
	"\240\145\168\179-\240\145\168\185" .. -- U+11A33-U+11A39
	"\240\145\168\187-\240\145\168\190" .. -- U+11A3B-U+11A3E
	"\240\145\169\135" .. -- U+11A47
	"\240\145\169\145-\240\145\169\155" .. -- U+11A51-U+11A5B
	"\240\145\170\138-\240\145\170\153" .. -- U+11A8A-U+11A99
	"\240\145\176\175-\240\145\176\182" .. -- U+11C2F-U+11C36
	"\240\145\176\184-\240\145\176\191" .. -- U+11C38-U+11C3F
	"\240\145\178\146-\240\145\178\167" .. -- U+11C92-U+11CA7
	"\240\145\178\169-\240\145\178\182" .. -- U+11CA9-U+11CB6
	"\240\145\180\177-\240\145\180\182" .. -- U+11D31-U+11D36
	"\240\145\180\186" .. -- U+11D3A
	"\240\145\180\188" .. -- U+11D3C
	"\240\145\180\189" .. -- U+11D3D
	"\240\145\180\191-\240\145\181\133" .. -- U+11D3F-U+11D45
	"\240\145\181\135" .. -- U+11D47
	"\240\145\182\138-\240\145\182\142" .. -- U+11D8A-U+11D8E
	"\240\145\182\144" .. -- U+11D90
	"\240\145\182\145" .. -- U+11D91
	"\240\145\182\147-\240\145\182\151" .. -- U+11D93-U+11D97
	"\240\145\187\179-\240\145\187\182" .. -- U+11EF3-U+11EF6
	"\240\145\188\128" .. -- U+11F00
	"\240\145\188\129" .. -- U+11F01
	"\240\145\188\131" .. -- U+11F03
	"\240\145\188\180-\240\145\188\186" .. -- U+11F34-U+11F3A
	"\240\145\188\190-\240\145\189\130" .. -- U+11F3E-U+11F42
	"\240\145\189\154" .. -- U+11F5A
	"\240\147\145\128" .. -- U+13440
	"\240\147\145\135-\240\147\145\149" .. -- U+13447-U+13455
	"\240\150\132\158-\240\150\132\175" .. -- U+1611E-U+1612F
	"\240\150\171\176-\240\150\171\180" .. -- U+16AF0-U+16AF4
	"\240\150\172\176-\240\150\172\182" .. -- U+16B30-U+16B36
	"\240\150\189\143" .. -- U+16F4F
	"\240\150\189\145-\240\150\190\135" .. -- U+16F51-U+16F87
	"\240\150\190\143-\240\150\190\146" .. -- U+16F8F-U+16F92
	"\240\150\191\164" .. -- U+16FE4
	"\240\150\191\176" .. -- U+16FF0
	"\240\150\191\177" .. -- U+16FF1
	"\240\155\178\157" .. -- U+1BC9D
	"\240\155\178\158" .. -- U+1BC9E
	"\240\156\188\128-\240\156\188\173" .. -- U+1CF00-U+1CF2D
	"\240\156\188\176-\240\156\189\134" .. -- U+1CF30-U+1CF46
	"\240\157\133\165-\240\157\133\169" .. -- U+1D165-U+1D169
	"\240\157\133\173-\240\157\133\178" .. -- U+1D16D-U+1D172
	"\240\157\133\187-\240\157\134\130" .. -- U+1D17B-U+1D182
	"\240\157\134\133-\240\157\134\139" .. -- U+1D185-U+1D18B
	"\240\157\134\170-\240\157\134\173" .. -- U+1D1AA-U+1D1AD
	"\240\157\137\130-\240\157\137\132" .. -- U+1D242-U+1D244
	"\240\157\168\128-\240\157\168\182" .. -- U+1DA00-U+1DA36
	"\240\157\168\187-\240\157\169\172" .. -- U+1DA3B-U+1DA6C
	"\240\157\169\181" .. -- U+1DA75
	"\240\157\170\132" .. -- U+1DA84
	"\240\157\170\155-\240\157\170\159" .. -- U+1DA9B-U+1DA9F
	"\240\157\170\161-\240\157\170\175" .. -- U+1DAA1-U+1DAAF
	"\240\158\128\128-\240\158\128\134" .. -- U+1E000-U+1E006
	"\240\158\128\136-\240\158\128\152" .. -- U+1E008-U+1E018
	"\240\158\128\155-\240\158\128\161" .. -- U+1E01B-U+1E021
	"\240\158\128\163" .. -- U+1E023
	"\240\158\128\164" .. -- U+1E024
	"\240\158\128\166-\240\158\128\170" .. -- U+1E026-U+1E02A
	"\240\158\130\143" .. -- U+1E08F
	"\240\158\132\176-\240\158\132\182" .. -- U+1E130-U+1E136
	"\240\158\138\174" .. -- U+1E2AE
	"\240\158\139\172-\240\158\139\175" .. -- U+1E2EC-U+1E2EF
	"\240\158\147\172-\240\158\147\175" .. -- U+1E4EC-U+1E4EF
	"\240\158\151\174" .. -- U+1E5EE
	"\240\158\151\175" .. -- U+1E5EF
	"\240\158\163\144-\240\158\163\150" .. -- U+1E8D0-U+1E8D6
	"\240\158\165\132-\240\158\165\138") -- U+1E944-U+1E94A

-- Double combining characters.
-- Charset: [[:M:]&[:Canonical_Combining_Class=/^Double_/:]&[:^subhead=Grapheme joiner:]&[:^Variation_Selector=Yes:]]
local comb_chars_double =
	"\205\156-\205\162" .. -- U+035C-U+0362
	"\225\183\141" .. -- U+1DCD
	"\225\183\188" -- U+1DFC
	
-- Variation selectors etc.; separated out so that we don't get categories for them.
-- Charset: [[:M:]&[[:subhead=Grapheme joiner:][:Variation_Selector=Yes:]]].
local comb_chars_other =
	"\205\143" .. -- U+034F
	"\225\160\139-\225\160\141" .. -- U+180B-U+180D
	"\225\160\143" .. -- U+180F
	"\239\184\128-\239\184\143" .. -- U+FE00-U+FE0F
	"\243\160\132\128-\243\160\135\175" -- U+E0100-U+E01EF

local comb_chars_all = comb_chars_single .. comb_chars_double .. comb_chars_other

local comb_chars = {
	combined_single = "[^" .. comb_chars_all .. "][" .. comb_chars_single .. comb_chars_other .. "]+%f[^" .. comb_chars_all .. "]",
	combined_double = "[^" .. comb_chars_all .. "][" .. comb_chars_single .. comb_chars_other .. "]*[" .. comb_chars_double .. "]+[" .. comb_chars_all .. "]*.[" .. comb_chars_single .. comb_chars_other .. "]*",
	diacritics_single = "[" .. comb_chars_single .. "]",
	diacritics_double = "[" .. comb_chars_double .. "]",
	diacritics_all = "[" .. comb_chars_all .. "]"
}

-- Somewhat curated list from https://unicode.org/Public/emoji/16.0/emoji-sequences.txt.
-- NOTE: There are lots more emoji sequences involving non-emoji Plane 0 symbols followed by 0xFE0F, which we don't
-- (yet?) handle.
local emoji_chars =
	"\226\140\154" .. -- U+231A (⌚)
	"\226\140\155" .. -- U+231B (⌛)
	"\226\140\168" .. -- U+2328 (⌨)
	"\226\143\143" .. -- U+23CF (⏏)
	"\226\143\169-\226\143\179" .. -- U+23E9-U+23F3 (⏩-⏳)
	"\226\143\184-\226\143\186" .. -- U+23F8-U+23FA (⏸-⏺)
	"\226\150\170" .. -- U+25AA (▪)
	"\226\150\171" .. -- U+25AB (▫)
	"\226\150\182" .. -- U+25B6 (▶)
	"\226\151\128" .. -- U+25C0 (◀)
	"\226\151\187-\226\151\190" .. -- U+25FB-U+25FE (◻-◾)
	"\226\152\128-\226\152\132" .. -- U+2600-U+2604 (☀-☄)
	"\226\152\142" .. -- U+260E (☎)
	"\226\152\145" .. -- U+2611 (☑)
	"\226\152\148" .. -- U+2614 (☔)
	"\226\152\149" .. -- U+2615 (☕)
	"\226\152\152" .. -- U+2618 (☘)
	"\226\152\157" .. -- U+261D (☝)
	"\226\152\160" .. -- U+2620 (☠)
	"\226\152\162" .. -- U+2622 (☢)
	"\226\152\163" .. -- U+2623 (☣)
	"\226\152\166" .. -- U+2626 (☦)
	"\226\152\170" .. -- U+262A (☪)
	"\226\152\174" .. -- U+262E (☮)
	"\226\152\175" .. -- U+262F (☯)
	"\226\152\184-\226\152\186" .. -- U+2638-U+263A (☸-☺)
	"\226\153\136-\226\153\147" .. -- U+2648-U+2653 (♈-♓)
	"\226\153\159" .. -- U+265F (♟)
	"\226\153\160" .. -- U+2660 (♠)
	"\226\153\163" .. -- U+2663 (♣)
	"\226\153\165" .. -- U+2665 (♥)
	"\226\153\166" .. -- U+2666 (♦)
	"\226\153\168" .. -- U+2668 (♨)
	"\226\153\187" .. -- U+267B (♻)
	"\226\153\190" .. -- U+267E (♾)
	"\226\153\191" .. -- U+267F (♿)
	"\226\154\146-\226\154\151" .. -- U+2692-U+2697 (⚒-⚗)
	"\226\154\153" .. -- U+2699 (⚙)
	"\226\154\155" .. -- U+269B (⚛)
	"\226\154\156" .. -- U+269C (⚜)
	"\226\154\160" .. -- U+26A0 (⚠)
	"\226\154\161" .. -- U+26A1 (⚡)
	"\226\154\170" .. -- U+26AA (⚪)
	"\226\154\171" .. -- U+26AB (⚫)
	"\226\154\176" .. -- U+26B0 (⚰)
	"\226\154\177" .. -- U+26B1 (⚱)
	"\226\154\189" .. -- U+26BD (⚽)
	"\226\154\190" .. -- U+26BE (⚾)
	"\226\155\132" .. -- U+26C4 (⛄)
	"\226\155\133" .. -- U+26C5 (⛅)
	"\226\155\136" .. -- U+26C8 (⛈)
	"\226\155\142" .. -- U+26CE (⛎)
	"\226\155\143" .. -- U+26CF (⛏)
	"\226\155\145" .. -- U+26D1 (⛑)
	"\226\155\147" .. -- U+26D3 (⛓)
	"\226\155\148" .. -- U+26D4 (⛔)
	"\226\155\169" .. -- U+26E9 (⛩)
	"\226\155\170" .. -- U+26EA (⛪)
	"\226\155\176-\226\155\181" .. -- U+26F0-U+26F5 (⛰-⛵)
	"\226\155\183-\226\155\186" .. -- U+26F7-U+26FA (⛷-⛺)
	"\226\155\189" .. -- U+26FD (⛽)
	"\226\156\130" .. -- U+2702 (✂)
	"\226\156\133" .. -- U+2705 (✅)
	"\226\156\136-\226\156\141" .. -- U+2708-U+270D (✈-✍)
	"\226\156\143" .. -- U+270F (✏)
	"\226\156\146" .. -- U+2712 (✒)
	"\226\156\148" .. -- U+2714 (✔)
	"\226\156\150" .. -- U+2716 (✖)
	"\226\156\157" .. -- U+271D (✝)
	"\226\156\161" .. -- U+2721 (✡)
	"\226\156\168" .. -- U+2728 (✨)
	"\226\156\179" .. -- U+2733 (✳)
	"\226\156\180" .. -- U+2734 (✴)
	"\226\157\132" .. -- U+2744 (❄)
	"\226\157\135" .. -- U+2747 (❇)
	"\226\157\140" .. -- U+274C (❌)
	"\226\157\142" .. -- U+274E (❎)
	"\226\157\147-\226\157\149" .. -- U+2753-U+2755 (❓-❕)
	"\226\157\151" .. -- U+2757 (❗)
	"\226\157\163" .. -- U+2763 (❣)
	"\226\157\164" .. -- U+2764 (❤)
	"\226\158\149-\226\158\151" .. -- U+2795-U+2797 (➕-➗)
	"\226\158\161" .. -- U+27A1 (➡)
	"\226\158\176" .. -- U+27B0 (➰)
	"\226\158\191" .. -- U+27BF (➿)
	"\226\164\180" .. -- U+2934 (⤴)
	"\226\164\181" .. -- U+2935 (⤵)
	"\226\172\133-\226\172\135" .. -- U+2B05-U+2B07 (⬅-⬇)
	"\226\172\155" .. -- U+2B1B (⬛)
	"\226\172\156" .. -- U+2B1C (⬜)
	"\226\173\144" .. -- U+2B50 (⭐)
	"\226\173\149" .. -- U+2B55 (⭕)
	"\227\128\176" .. -- U+3030 (〰)
	"\227\128\189" .. -- U+303D (〽)
	"\227\138\151" .. -- U+3297 (㊗)
	"\227\138\153" .. -- U+3299 (㊙)
	"\240\159\128\132" .. -- U+1F004 (🀄)
	"\240\159\131\143" .. -- U+1F0CF (🃏)
	"\240\159\133\176" .. -- U+1F170 (🅰)
	"\240\159\133\177" .. -- U+1F171 (🅱)
	"\240\159\133\190" .. -- U+1F17E (🅾)
	"\240\159\133\191" .. -- U+1F17F (🅿)
	"\240\159\134\142" .. -- U+1F18E (🆎)
	"\240\159\134\145-\240\159\134\154" .. -- U+1F191-U+1F19A (🆑-🆚)
	"\240\159\136\129" .. -- U+1F201 (🈁)
	"\240\159\136\130" .. -- U+1F202 (🈂)
	"\240\159\136\154" .. -- U+1F21A (🈚)
	"\240\159\136\175" .. -- U+1F22F (🈯)
	"\240\159\136\178-\240\159\136\186" .. -- U+1F232-U+1F23A (🈲-🈺)
	"\240\159\137\144" .. -- U+1F250 (🉐)
	"\240\159\137\145" .. -- U+1F251 (🉑)
	"\240\159\140\128-\240\159\153\143" .. -- U+1F300-U+1F64F (🌀-🙏)
	"\240\159\154\128-\240\159\155\151" .. -- U+1F680-U+1F6D7 (🚀-🛗)
	"\240\159\155\156-\240\159\155\172" .. -- U+1F6DC-U+1F6EC (🛜-🛬)
	"\240\159\155\176-\240\159\155\188" .. -- U+1F6F0-U+1F6FC (🛰-🛼)
	"\240\159\159\160-\240\159\159\171" .. -- U+1F7E0-U+1F7EB (🟠-🟫)
	"\240\159\159\176" .. -- U+1F7F0 (🟰)
	"\240\159\164\140-\240\159\169\147" .. -- U+1F90C-U+1FA53 (🤌-🩓)
	"\240\159\169\160-\240\159\169\173" .. -- U+1FA60-U+1FA6D (🩠-🩭)
	"\240\159\169\176-\240\159\169\188" .. -- U+1FA70-U+1FA7C (🩰-🩼)
	"\240\159\170\128-\240\159\170\137" .. -- U+1FA80-U+1FA89 (🪀-🪉)
	"\240\159\170\143-\240\159\171\134" .. -- U+1FA8F-U+1FAC6 (🪏-🫆)
	"\240\159\171\142-\240\159\171\156" .. -- U+1FACE-U+1FADC (🫎-🫜)
	"\240\159\171\159-\240\159\171\169" .. -- U+1FADF-U+1FAE9 (🫟-🫩)
	"\240\159\171\176-\240\159\171\184" -- U+1FAF0-U+1FAF8 (🫰-🫸)

local unsupported_characters = {}
for k, v in pairs(require("links/data.lua").unsupported_characters) do
	unsupported_characters[v] = k
end

-- Get the list of unsupported titles and invert it (so the keys are pagenames and values are canonical titles).
local unsupported_titles = {}
for k, v in pairs(require("links/data.lua").unsupported_titles) do
	unsupported_titles[v] = k
end

--[==[
Given a pagename (or {nil} for the current page), create and return a data structure describing the page. The returned
object includes the following fields:
* `comb_chars`: A table containing various Lua character class patterns for different types of combined characters
  (those that decompose into multiple characters in the NFD decomposition). The patterns are meant to be used with
  {mw.ustring.find()}. The keys are:
** `single`: Single combining characters (character + diacritic), without surrounding brackets;
** `double`: Double combining characters (character + diacritic + character), without surrounding brackets;
** `vs`: Variation selectors, without surrounding brackets;
** `all`: Concatenation of `single` + `double` + `vs`, without surrounding brackets;
** `diacritics_single`: Like `single` but with surrounding brackets;
** `diacritics_double`: Like `double` but with surrounding brackets;
** `diacritics_all`: Like `all` but with surrounding brackets;
** `combined_single`: Lua pattern for matching a spacing character followed by one or more single combining characters;
** `combined_double`: Lua pattern for matching a combination of two spacing characters separated by one or more double
   combining characters, possibly also with single combining characters;
* `emoji_pattern`: A Lua character class pattern (including surrounding brackets) that matches emojis. Meant to be used
  with {mw.ustring.find()}.
* `L2_list`: Ordered list of L2 headings on the page, with the extra key `n` that gives the length of the list.
* `L2_sections`: Lookup table of L2 headings on the page, where the key is the section number assigned by the preprocessor, and the value is the L2 heading name. Once an invocation has got its actual section number from get_current_L2 in [[Module:pages]], it can use this table to determine its parent L2. TODO: We could expand this to include subsections, to check POS headings are correct etc.
* `unsupported_titles`: Map from pagenames to canonical titles for unsupported-title pages.
* `namespace`: Namespace of the pagename.
* `ns`: Namespace table for the page from mw.site.namespaces (TODO: merge with `namespace` above).
* `full_raw_pagename`: Full version of the '''RAW''' pagename (i.e. unsupported-title pages aren't canonicalized);
  including the namespace and the root (portion before the slash).
* `pagename`: Canonicalized subpage portion of the pagename (unsupported-title pages are canonicalized).
* `decompose_pagename`: Equivalent of `pagename` in NFD decomposition.
* `pagename_len`: Length of `pagename` in Unicode chars, where combinations of spacing character + decomposed diacritic
  are treated as single characters.
* `explode_pagename`: Set of characters found in `pagename`. The keys are characters (where combinations of spacing
  character + decomposed diacritic are treated as single characters).
* `encoded_pagename`: FIXME: Document me.
* `pagename_defaultsort`: FIXME: Document me.
* `raw_defaultsort`: FIXME: Document me.
* `wikitext_topic_cat`: FIXME: Document me.
* `wikitext_langname_cat`: FIXME: Document me.
]==]

function export.process_page(pagename)
	local data = {
		comb_chars = comb_chars,
		emoji_pattern = "[" .. emoji_chars .. "]",
		unsupported_titles = unsupported_titles
	}
	
	local cats = {}
	data.cats = cats

	-- We cannot store `raw_title` in `data` because it contains a metatable.
	local raw_title
	local function bad_pagename()
		if not pagename then
			error("Internal error: Something wrong, `data.pagename` not specified but current title containg illegal characters")
		else
			error(("Bad value for `data.pagename`: '%s', which must not contain illegal characters"):format(pagename))
		end
	end
	if pagename then -- for testing, doc pages, etc.
		raw_title = new_title(pagename)
		if not raw_title then
			bad_pagename()
		end
	else
		raw_title = mw.title.getCurrentTitle()
	end
	data.namespace = raw_title.nsText
	data.ns = mw.site.namespaces[raw_title.namespace]
	data.full_raw_pagename = raw_title.fullText

	local frame = mw.getCurrentFrame()
	-- WARNING: `content` May be nil, e.g. if we're substing a template like {{ja-new}} on a not-yet-created page
	-- or if the module specifies the subpage as `data.pagename` (which many modules do) and we're in an Appendix
	-- or other non-mainspace page. We used to make the latter an error but there are too many modules that do it,
	-- and substing on a nonexistent page is totally legit, and we don't actually need to be able to access the
	-- content of the page.
	local content = raw_title:getContent()

	--Get the pagename.
	pagename = raw_title.subpageText
		:gsub("^Unsupported titles/(.*)", function(m)
			insert(cats, "Unsupported titles")
			return unsupported_titles[m] or (m:gsub("`.-`", unsupported_characters))
		end)
	-- Save pagename, as local variable will be destructively modified.
	data.pagename = pagename
	-- Decompose the pagename in Unicode normalization form D.
	data.decompose_pagename = toNFD(pagename)
	-- Explode the current page name into a character table, taking decomposed combining characters into account.
	local explode_pagename = {}
	local pagename_len = 0
	local function explode(char)
		explode_pagename[char] = true
		pagename_len = pagename_len + 1
		return ""
	end
	pagename = ugsub(pagename, comb_chars.combined_double, explode)
	pagename = ugsub(pagename, comb_chars.combined_single, explode)
		:gsub(".[\128-\191]*", explode)

	data.explode_pagename = explode_pagename
	data.pagename_len = pagename_len
	
	-- Generate DEFAULTSORT.
	data.encoded_pagename = encode_entities(data.pagename)
	data.pagename_defaultsort = get_lang("mul"):makeSortKey(data.encoded_pagename)
	frame:callParserFunction(
		"DEFAULTSORT",
		data.pagename_defaultsort
	)
	data.raw_defaultsort = raw_title.text:uupper()
	
	-- Make `L2_list` and `L2_sections`, note raw wikitext use of {{DEFAULTSORT:}} and {{DISPLAYTITLE:}}, then add categories if any unwanted L1 headings are found, the L2 headings are in the wrong order, or they don't match a canonical language name.
	-- Note: HTML comments shouldn't be removed from `content` until after this step, as they can affect the result.
	do
		local L2_list, L2_list_len, L2_sections, sort_cache, prev = {}, 0, {}, {}
		local new_cats, L2_wrong_order = {}
		
		local function get_weight(L2)
			if L2 == "Translingual" then
				return "\1"
			elseif L2 == "English" then
				return "\2"
			elseif match(L2, "^[%z\1-\b\14-!#-&(-,.-\127]+$") then
				return L2
			end
			local weight = sort_cache[L2]
			if weight then
				return weight
			end
			weight = toNFC(ugsub(ugsub(toNFD(L2), "[" .. comb_chars_all .. "'\"ʻʼ]+", ""), "[%s%-]+", " "))
			sort_cache[L2] = weight
			return weight
		end
		
		local function handle_heading(heading)
			local level = heading.level
			if level > 2 then
				return
			end
			local name = heading:get_name()
			-- heading:get_name() will return nil if there are any newline characters in the preprocessed heading name (e.g. from an expanded template). In such cases, the preprocessor section count still increments (since it's calculated pre-expansion), but the heading will fail, so the L2 count shouldn't be incremented.
			if name == nil then
				return
			end
			L2_list_len = L2_list_len + 1
			L2_list[L2_list_len] = name
			L2_sections[heading.section] = name
			-- Also add any L1s, since they terminate the preceding L2, but add a maintenance category since it's probably a mistake.
			if level == 1 then
				new_cats["Pages with unwanted L1 headings"] = true
			end
			-- Check the heading is in the right order.
			-- FIXME: we need a more sophisticated sorting method which handles non-diacritic special characters (e.g. Magɨ).
			if prev and not (
				L2_wrong_order or
				string_sort(get_weight(prev), get_weight(name))
			) then
				new_cats["Pages with language headings in the wrong order"] = true
				L2_wrong_order = true
			end
			-- Check it's a canonical language name.
			if not langnames[name] then
				new_cats["Pages with nonstandard language headings"] = true
			end
			prev = name
		end
		
		local function handle_template(template)
			local name = template:get_name()
			if name == "DEFAULTSORT:" then
				new_cats["Pages with DEFAULTSORT conflicts"] = true
			elseif name == "DISPLAYTITLE:" then
				new_cats["Pages with DISPLAYTITLE conflicts"] = true
			end
		end
		
		if content then
			for node in parse(content):__pairs("next_node") do
				local node_class = class_else_type(node)
				if node_class == "heading" then
					handle_heading(node)
				elseif node_class == "template" then
					handle_template(node)
				elseif node_class == "parameter" then
					new_cats["Pages with raw triple-brace template parameters"] = true
				end
			end
		end
		
		L2_list.n = L2_list_len
		data.L2_list = L2_list
		data.L2_sections = L2_sections
		
		insert(cats, get_category("Pages with entries"))
		insert(cats, get_category("Pages with %s entr%s"):format(L2_list_len, L2_list_len == 1 and "y" or "ies"))
		
		for cat in pairs(new_cats) do
			insert(cats, get_category(cat))
		end
	end

	------ 4. Parse page for maintenance categories. ------
	-- Use of tab characters.
	if content and find(content, "\t", 1, true) then
		insert(cats, get_category("Pages with tab characters"))
	end
	-- Unencoded character(s) in title.
	local IDS = list_to_set{"⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻", "⿼", "⿽", "⿾", "⿿", "㇯"}
	for char in pairs(explode_pagename) do
		if IDS[char] and char ~= data.pagename then
			insert(cats, "Terms containing unencoded characters")
			break
		end
	end

	-- Raw wikitext use of a topic or langname category. Also check if any raw sortkeys have been used.
	do
		local wikitext_topic_cat = {}
		local wikitext_langname_cat = {}
		local raw_sortkey
		
		-- If a raw sortkey has been found, add it to the relevant table.
		-- If there's no table (or the index is just `true`), create one first.
		local function add_cat_table(t, lang, sortkey)
			local t_lang = t[lang]
			if not sortkey then
				if not t_lang then
					t[lang] = true
				end
				return
			elseif t_lang == true or not t_lang then
				t_lang = {}
				t[lang] = t_lang
			end
			t_lang[uupper(decode_entities(sortkey))] = true
		end
		
		local function process_category(content, cat, colon, nxt)
			local pipe = find(cat, "|", colon + 1, true)
			-- Categories cannot end "|]]".
			if pipe == #cat then
				return
			end
			local title = new_title(pipe and sub(cat, 1, pipe - 1) or cat)
			if not (title and title.namespace == 14) then
				return
			end
			-- Get the sortkey (if any), then canonicalize category title.
			local sortkey = pipe and sub(cat, pipe + 1) or nil
			cat = title.text
			if sortkey then
				raw_sortkey = true
				-- If the sortkey contains "[", the first "]" of a final "]]]" is treated as part of the sortkey.
				if find(sortkey, "[", 1, true) and sub(content, nxt, nxt) == "]" then
					sortkey = sortkey .. "]"
				end
			end
			local code = match(cat, "^([%w%-.]+):")
			if code then
				add_cat_table(wikitext_topic_cat, code, sortkey)
				return
			end
			-- Split by word.
			cat = split(cat, " ", true, true)
			-- Formerly we looked for the language name anywhere in the category. This is simply wrong
			-- because there are no categories like 'Alsatian French lemmas' (only L2 languages
			-- have langname categories), but doing it this way wrongly catches things like [[Category:Shapsug Adyghe]]
			-- in [[Category:Adyghe entries with language name categories using raw markup]].
			local n = #cat - 1
			if n <= 0 then
				return
			end
			-- Go from longest to shortest and stop once we've found a language name. Going from shortest
			-- to longest or not stopping after a match risks falsely matching (e.g.) German Low German
			-- categories as German.
			repeat
				local name = concat(cat, " ", 1, n)
				if langnames[name] then
					add_cat_table(wikitext_langname_cat, name, sortkey)
					return
				end
				n = n - 1
			until n == 0
		end
		
		if content then
			-- Remove comments, then iterate over category links.
			content = remove_comments(content, "BOTH")
			local head = find(content, "[[", 1, true)
			while head do
				local close = find(content, "]]", head + 2, true)
				if not close then
					break
				end
				-- Make sure there are no intervening "[[" between head and close.
				local open = find(content, "[[", head + 2, true)
				while open and open < close do
					head = open
					open = find(content, "[[", head + 2, true)
				end
				local cat = sub(content, head + 2, close - 1)
				-- Locate the colon, and weed out most unwanted links. "[ _\128-\244]*" catches valid whitespace, and ensures any category links using the colon trick are ignored. We match all non-ASCII characters, as there could be multibyte spaces, and mw.title.new will filter out any remaining false-positives; this is a lot faster than running mw.title.new on every link.
				local colon = match(cat, "^[ _\128-\244]*[Cc][Aa][Tt][EeGgOoRrYy _\128-\244]*():")
				if colon then
					process_category(content, cat, colon, close + 2)
				end
				head = open
			end
		end
		
		data.wikitext_topic_cat = wikitext_topic_cat
		data.wikitext_langname_cat = wikitext_langname_cat
		if raw_sortkey then
			insert(cats, get_category("Pages with raw sortkeys"))
		end
	end

	return data
end

return export
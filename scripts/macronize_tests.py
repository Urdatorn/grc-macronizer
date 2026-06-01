'''
Here you can try the macronizer on the included test texts.
Just comment out the input with the text you want, and comment out everything else.

In general, Supplices (ἱκέτιδες in Greek) is in verse and 
a prosodically much more complex text than the straight-forward prose story Anabasis.
This is not a benchmark: I have added quite a few of the proper names of Anabasis to the custom db, 
as an example of the high results that can be achieved by manually "localizing" the macronizer to your target text.

A good work flow is to first run the macronizer as-is on your target text, inspect the list of un-disambiguated words in diagnostics/still_ambiguous, 
and then manually add the most common of them to the db/custom.py. 
Of course, "manually" could mean using a good LLM with research capabilities. 
'''

import re
import time

from grc_macronizer import Macronizer
from grc_macronizer.tests.hiketides import hiketides # "Supplices" by Sophocles
from grc_macronizer.tests.anabasis import anabasis, anabasis_medium, anabasis_short # "Anabasis" by Xenophon

from grc_utils import colour_dichrona_in_open_syllables, macronization_stats

macronizer = Macronizer(no_hypotactic=False, make_prints=True, lowercase=True)

#input = "χρὴ γι^νώσκειν ὅτι^ πά_σης τῆς γῆς ὁ περί^μετρος στά^δι^ά^ ἐστι^ δι^σχί_λι^α^ καὶ μυ_ρι^ά^δες εἴκοσι^ πέντε μῆκος δὲ τῆς ἡμετέρα_ς οἰκουμένης ἀ^πὸ στόμα^τος γάγγου ἕως γαδείρων στά^δι^α^ ὀκτακισμύρια^ τρι^σχί_λι^α^ ὀκ τακόσια^ τὸ δὲ πλά^τος ἀ^πὸ τῆς αἰθιοπικῆς θα^λάσσης ἕως τοῦ τανάϊδος ποτα^μοῦ στά^δι^α^ τρισμύρια^ πεντακισχίλια^ τὸ δὲ μετα^ξὺ^ εὐφράτου καὶ τίγριδος ποτα^μοῦ ὃ κα^λεῖται μεσοποτάμιον δι^ά^στημα^ ἔχει στα^δί^ων τρι^σχι_λί^ων ταύτην τὴν ἀναμέτρησι^ν πεποίηκεν ἐρατοσθένης ὁ τῶν ἀρχαίων μαθητικώτατος ἀ^πὸ τοῦ βυζαντίου εἰς τὸ σωσθένιον στά^δι^α^ ὀγδοήκοντα^ μίλια^ δέ^κα^ καὶ ἥμι^συ^ ἀ^πὸ δὲ τοῦ σωσθενίου εἰς τὸ ἱερὸν στά^δι^α^ τεσσα^ρά^κοντα^ μίλια^ πέντε ἥμι^συ^ τὸ πᾶν μίλια^ δεκαέξ ἀ^πὸ δὲ τοῦ ἱ^εροῦ διὸς οὐρίου ἤτοι στόμα^τος τοῦ πόντου ἕως τοῦ ἱεροῦ στόμα^τος τοῦ ἴστρου ποτα^μοῦ στά^δι^α^ τρι^σχί_λι^α^ ἑξα^κόσι^α^ τεσσα^ρά^κοντα^ μίλια^ τετρα^κόσι^α^ ὀγδοήκοντα^ πέντε ἥμι^συ^ ἀπὸ δὲ τοῦ ἱεροῦ διὸς οὐρίου ἕως βορυσθένους ποτα^μοῦ τοῦ καὶ δανάπρεως κα^λουμένου στά^δι^α^ πεντακισχίλια^ ἑξα^κόσι^α^ μίλια^ ἑπτα^κόσι^α^ τεσσαρακονταὲξ ἥμι^συ^ ἀπὸ δὲ τοῦ ἱεροῦ διὸς οὐρίου ἕως πορθμίας πόλεως τῆς ἐν τέλει τῆς εὐρώπης τῶν τοῦ πόντου μερῶν τῆς ἐν τῷ στομί^ῳ τῆς μαιώτιδος λίμνης ἤτοι βοσπόρου τοῦ κιμμερίου κα^λουμένου στά^δι^α^ μύρια^ χί_λι^α^ ἑκα^τόν μίλια^ χί_λι^α^ τετρα^κόσι^α^ ὀγδοήκοντα^ λέγεται δὲ τῆς εὐρώπης τῆς ποντικῆς ὁ περίπλους ἴ^σος εἶναι τῶ περίπλῳ τῶν τῆς ἀσίας μερῶν ἀπὸ δὲ τοῦ ἱεροῦ διὸς οὐρίου ἕως ἀμισοῦ στά^δι^α^ τετρακισχίλια^ ἑξα^κόσι^α^ ἐξήκοντα^ μίλια^ ἑξα^κόσι^α^ εἰκοσιὲν ἥμι^συ^ ἀπὸ δὲ ἀμισοῦ ἕως τοῦ φάσεως ποτα^μοῦ στά^δι^α^ τρι^σχί_λι^α^ ὀκτα^κόσι^α^ δύ^ο μίλια^ πεντα^κόσι^α^ ἑπτά^ ἀπὸ δὲ τοῦ φάσεως ποτα^μοῦ ἕως τοῦ στόμα^τος τῆς μαιώτιδος λίμνης ἤτοι ἕως τῆς ἀχιλλείου κώμης στά^δι^α^ τετρακισχίλια^ εἴκοσι^ πέντε μίλια^ πεντα^κόσι^α^ τριακονταὲξ ἥμι^συ^ ὡς γί_νεσθαι ἀπὸ τοῦ ἱεροῦ διὸς οὐρίου ἕως τοῦ στόμα^τος τῆς μαιώτιδος λίμνης στά^δι^α^ μύρια^ δισ χί_λι^α^ τετρα^κόσι^α^ ὀγδοήκοντα^ ἑπτὰ^ μίλια^ χί_λι^α^ ἑξα^κόσι^α^ ἐξήκοντα^ πέντε ἥμι^συ^ ὁμοῦ γί_νεται ὁ περίπλους τοῦ εὐξείνου πόντου τῶν τε δεξι^ῶν τῶν πα^ρὰ^ τὴν ἀσίαν μερῶν τοῦ πόντου ἀ^ριστερῶν δὲ τῶν πα^ρὰ^ τὴν εὐρώπην μερῶν τοῦ πόντου ἀπὸ τοῦ ἱεροῦ διὸς οὐρίου στά^δι^α^ δισμύρια^ τρι^σχί_λι^α^ πεντα^κόσι^α^ ὀγδοήκοντα^ ἑπτὰ^ μίλια^ τρι^σχί_λι^α^ ἑκα^τὸν τεσσα^ρά^κοντα^ πέντε ἔστι δὲ καὶ ὁ περίπλους τῆς μαιώτιδος λίμνης στά^δι^α^ ἐννακισχίλια^ μίλια^ χί_λι^α^ δι^α_κόσι^α^ περὶ τοῦ στα^δί^ου τὸ στά^δι^ον πήχεις ἔχει τετρα^κοσί^ους πόδα^ς ὀκτα^κοσί^ους ὀργυιὰ_ς ἑκα^τὸν τρι^ά_κοντα^ τρεῖς ἥμι^συ^ περὶ τοῦ μιλί^ου τὸ μίλιον ἔχει στά^δι^α^ ἑπτὰ^ ἥμι^συ^ πήχεις τρι^σχι_λί^ους πόδα^ς ἑξακισχιλί^ους περὶ τοῦ ἐνι^αυτοῦ ἅπας ἔχει ὥρα_ς ὀκτακισχιλία_ς ἑπτα^κοσί^α_ς ἐξήκοντα^ ἓξ ἡμέρα_ς τρι^α_κοσί^α_ς ἑξήκοντα^ πέντε καὶ τέταρτον".replace("^", "").replace("_", "")
#input = hiketides
input = anabasis_short
#input = anabasis_medium
#input = anabasis

time_start = time.time()
output = macronizer.macronize(input)
time_end = time.time()

numerator, denominator, ratio = macronization_stats(input, output) # use this if you want to use the stats
print(f"Total macronization = {numerator}/{denominator} = {ratio:.2%}")

output_split = [sentence for sentence in re.findall(r'([^.\n;\u037e]+[.;\u037e]?)\n?', output) if sentence]
for line in output_split[:10]:
    print(colour_dichrona_in_open_syllables(line))

print(f"Time taken: {time_end - time_start:.2f} seconds")
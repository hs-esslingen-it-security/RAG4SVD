import re

import execjs
import javalang

ctx = execjs.compile("""
const parser = require('@solidity-parser/parser');
function getAst(code){
    const input = `
    contract c {` +
        code
            + `
    }`
    try {
        var ast = parser.parse(input)
        return ast
    } catch (e) {
        if (e instanceof parser.ParserError) {
            console.error(e.errors)
            var ast = {"type": "SourceUnit"}
            return ast
        }
    }
}
""")


def VLR(a):
    tmp_list = []
    key_list = []
    if isinstance(a,dict):
        key_list = a.keys()
    for key in key_list:
        if key == 'type':
            tmp_list.append(a['type'])
        elif isinstance(a[key],dict):
            tmp_list.extend(VLR(a[key]))
        elif isinstance(a[key],list):
            for k in a[key]:
                tmp_list.extend(VLR(k))
    return tmp_list

def SBT(a):
    tmp_list = []
    tmp_list.append("(")
    key_list = []
    if isinstance(a, dict):
        key_list = a.keys()
    for key in key_list:
        if key == 'type':
            tmp_list.append(a['type'])

        elif isinstance(a[key], dict):
            tmp_list.extend(VLR(a[key]))
        elif isinstance(a[key], list):
            for k in a[key]:
                tmp_list.extend(VLR(k))
    tmp_list.append(")")
    tmp_list.append(a['type'])
    return tmp_list

#
result = ctx.call("getAst", """
  function balanceOf(address addr) constant public returns (uint256) {
  	return data.balanceOf(addr);
  }
""")

# print(result)
# result = VLR(result)
# print(" ".join(result))

def get_ast(code):
    try:
        ast = ctx.call("getAst", code)
        result = ' '.join(VLR(ast))
    except:
        result = 'SourceUnit'
    return result

def get_sbt(code):
    try:
        ast = ctx.call("getAst", code)
        result = ' '.join(SBT(ast))
    except:
        result = 'SourceUnit'
    return result

def hump2underline(hunp_str):
    '''
    驼峰形式字符串转成下划线形式
    :param hunp_str: 驼峰形式字符串
    :return: 字母全小写的下划线形式字符串
    '''
    p = re.compile(r'([a-z]|\d)([A-Z])')
    sub = re.sub(p, r'\1 \2', hunp_str).lower()
    return sub

def process_source(code):
    code = code.replace('\n',' ').strip()
    try:
        tokens = list(javalang.tokenizer.tokenize(code))
        tks = []
        for tk in tokens:
            if tk.__class__.__name__ == 'String' or tk.__class__.__name__ == 'Character':
                tks.append('STR_')
            elif 'Integer' in tk.__class__.__name__ or 'FloatingPoint' in tk.__class__.__name__:
                tks.append('NUM_')
            elif tk.__class__.__name__ == 'Boolean':
                tks.append('BOOL_')
            else:
                tks.append(hump2underline(tk.value))
    except Exception:
        code = code.replace("\r","")
        pattern = r',|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
        result_list = re.split(pattern, code)
        tks = [hump2underline(t) for t in result_list]
    return " ".join(tks)


from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

def get_wordnet_pos(tag):
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.VERB
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return None

def getOriginSentence(sentence):
    tokens = word_tokenize(sentence) 
    tagged_sent = pos_tag(tokens) 

    wnl = WordNetLemmatizer()
    lemmas_sent = []
    for tag in tagged_sent:
        wordnet_pos = get_wordnet_pos(tag[1]) or wordnet.NOUN
        lemmas_sent.append(wnl.lemmatize(tag[0], pos=wordnet_pos).lower())  
    return " ".join(lemmas_sent)
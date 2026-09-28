package llm4vuln

import com.google.gson.Gson
import java.io.File

fun main(args: Array<String>) {
    if (args.size != 3) {
        println("Args: [project_path] [class_name] [method_name]")
    }
    // run the parser
    val parser = Parser(args[0])
    parser.parseAll()

    // dump the result
    val jsonResult = HashMap<String, Any>()
    jsonResult["code"] = parser.getSource(args[1], args[2])
    jsonResult["related"] = parser.getCallees(args[1], args[2])
    val gson = Gson()
    val strResult = gson.toJson(jsonResult)

    // save to file
    try {
        File("output.json").writeText(strResult)
    } catch (e: Exception) {
        e.printStackTrace()
    }
}
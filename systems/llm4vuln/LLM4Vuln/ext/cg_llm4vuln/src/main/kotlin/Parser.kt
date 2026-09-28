package llm4vuln

import com.github.javaparser.JavaParser
import com.github.javaparser.ParserConfiguration
import com.github.javaparser.ast.CompilationUnit
import com.github.javaparser.ast.expr.MethodCallExpr
import com.github.javaparser.symbolsolver.JavaSymbolSolver
import com.github.javaparser.symbolsolver.javaparsermodel.declarations.JavaParserMethodDeclaration
import com.github.javaparser.symbolsolver.resolution.typesolvers.CombinedTypeSolver
import com.github.javaparser.symbolsolver.resolution.typesolvers.JavaParserTypeSolver
import com.github.javaparser.symbolsolver.resolution.typesolvers.ReflectionTypeSolver
import com.github.javaparser.utils.SourceRoot
import javassist.compiler.ast.CallExpr
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

class Parser(private val projectAbsolutePath: String) {
    private val compilationUnits = ArrayList<CompilationUnit>()

    fun parse(path: Path) {
        // setup symbol solver
        val combinedTypeSolver = CombinedTypeSolver()
        combinedTypeSolver.add(JavaParserTypeSolver(path))
        val configuration = ParserConfiguration().setSymbolResolver(JavaSymbolSolver(combinedTypeSolver))
        // setup source code parser
        val sourceRoot = SourceRoot(path, configuration)
        val parseResults = sourceRoot.tryToParse()
        // save success parse result
        for (parseResult in parseResults) {
            parseResult.result.orElse(null)?.let { compilationUnits.add(it) }
        }
    }

    fun parseAll() {
        // we assume that all the source code are in `src/main/java`
        Files.walk(Paths.get(projectAbsolutePath)).use { paths ->
            paths.filter {
                Files.isDirectory(it) && it.endsWith("src/main/java")
            }.forEach {
                parse(it)
            }
        }
    }

    fun getSource(className: String, methodName: String): String {
        for (cu in compilationUnits) {
            var findSource: String? = null
            cu.getClassByName(className).orElse(null)?.let { clazz ->
                if (className == methodName) {
                    if (clazz.constructors.size > 0) {
                        val method = clazz.constructors[0]
                        findSource = method.toString()
                    }
                } else {
                    clazz.getMethodsByName(methodName).let { methods ->
                        // select the first matched method
                        if (methods.size > 0) {
                            val method = methods[0]
                            findSource = method.toString()
                        }
                    }
                }
            }
            findSource?.run { return findSource!! }
        }
        return ""
    }

    fun getCallees(className: String, methodName: String): ArrayList<String> {
        for (cu in compilationUnits) {
            val callees = ArrayList<String>()
            cu.getClassByName(className).orElse(null)?.let { clazz ->
                if (className == methodName) {
                    if (clazz.constructors.size > 0) {
                        val method = clazz.constructors[0]
                        method.findAll(MethodCallExpr::class.java).forEach {
                            try {
                                val resolved = it.resolve()
                                if (resolved is JavaParserMethodDeclaration) {
                                    callees.add(resolved.wrappedNode.toString())
                                }
                            } catch (e: Exception) {
                                // do nothing
                            }
                        }
                    }
                } else {
                    clazz.getMethodsByName(methodName).let { methods ->
                        if (methods.size > 0) {
                            val method = methods[0]
                            method.findAll(MethodCallExpr::class.java).forEach {
                                try {
                                    val resolved = it.resolve()
                                    if (resolved is JavaParserMethodDeclaration) {
                                        callees.add(resolved.wrappedNode.toString())
                                    }
                                } catch (e: Exception) {
                                    // do nothing
                                }
                            }
                        }
                    }
                }
            }
            if (callees.size > 0) {
                return callees
            }
        }
        return ArrayList()
    }
}
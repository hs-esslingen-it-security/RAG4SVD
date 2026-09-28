plugins {
    kotlin("jvm") version "2.0.0"
}

group = "llm4vuln"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
    implementation("com.github.javaparser:javaparser-symbol-solver-core:3.26.1")
    implementation("com.github.javaparser:javaparser-core:3.26.1")
    implementation("com.google.code.gson:gson:2.11.0")
}

tasks.test {
    useJUnitPlatform()
}
kotlin {
    jvmToolchain(17)
}

tasks.jar{
    manifest {
        attributes["Main-Class"] = "llm4vuln.MainKt"
    }

    from(
        configurations.compileClasspath.get().map {
            if (it.isDirectory) {
                it
            } else {
                zipTree(it)
            }
        }
    )

    duplicatesStrategy = DuplicatesStrategy.INCLUDE
}
/*
 * vuln_02_format_string.c
 * 漏洞类型：格式化字符串漏洞 (Format String Bug)
 * 用户输入被直接传给 printf，攻击者可读写栈内存。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define LOG_SIZE 128

typedef struct {
    char message[LOG_SIZE];
    int  severity;
} LogEntry;

void log_init(LogEntry *entry, int sev) {
    memset(entry->message, 0, LOG_SIZE);
    entry->severity = sev;
}

void log_set_message(LogEntry *entry, const char *msg) {
    strncpy(entry->message, msg, LOG_SIZE - 1);
    entry->message[LOG_SIZE - 1] = '\0';
}

/* 漏洞：用户控制的 msg 直接作为 printf 的格式串 */
void log_print(const LogEntry *entry) {
    printf("[SEV %d] ", entry->severity);
    printf(entry->message);          /* VULN: format string */
    printf("\n");
}

void log_to_file(const LogEntry *entry, const char *path) {
    FILE *fp = fopen(path, "a");
    if (!fp) return;
    fprintf(fp, "[SEV %d] ", entry->severity);
    fprintf(fp, "%s\n", entry->message);  /* safe version */
    fclose(fp);
}

int classify_severity(const char *msg) {
    if (strstr(msg, "error")) return 3;
    if (strstr(msg, "warn"))  return 2;
    return 1;
}

void process_log(const char *user_input) {
    LogEntry entry;
    int sev = classify_severity(user_input);
    log_init(&entry, sev);
    log_set_message(&entry, user_input);
    log_print(&entry);                    /* VULN triggered here */
    log_to_file(&entry, "/tmp/app.log");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <log message>\n", argv[0]);
        return 1;
    }
    for (int i = 1; i < argc; i++) {
        process_log(argv[i]);
    }
    return 0;
}

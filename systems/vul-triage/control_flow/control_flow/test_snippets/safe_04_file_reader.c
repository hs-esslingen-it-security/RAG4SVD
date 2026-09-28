/*
 * safe_04_file_reader.c
 * 安全的文件逐行读取与统计 —— 无漏洞
 * 使用 fgets 读取固定缓冲区，不会溢出；文件句柄正确关闭。
 */
#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define LINE_MAX_LEN 256

typedef struct {
    int total_lines;
    int blank_lines;
    int total_chars;
    int alpha_chars;
} FileStats;

void init_stats(FileStats *s) {
    s->total_lines = 0;
    s->blank_lines = 0;
    s->total_chars = 0;
    s->alpha_chars = 0;
}

int is_blank_line(const char *line) {
    for (size_t i = 0; line[i] != '\0'; i++) {
        if (!isspace((unsigned char)line[i])) return 0;
    }
    return 1;
}

void count_chars(const char *line, int *total, int *alpha) {
    for (size_t i = 0; line[i] != '\0' && line[i] != '\n'; i++) {
        (*total)++;
        if (isalpha((unsigned char)line[i])) (*alpha)++;
    }
}

int read_file_stats(const char *path, FileStats *stats) {
    FILE *fp = fopen(path, "r");
    if (fp == NULL) {
        fprintf(stderr, "Cannot open file: %s\n", path);
        return -1;
    }

    init_stats(stats);
    char buf[LINE_MAX_LEN];

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        stats->total_lines++;
        if (is_blank_line(buf)) {
            stats->blank_lines++;
        }
        count_chars(buf, &stats->total_chars, &stats->alpha_chars);
    }

    fclose(fp);
    return 0;
}

void print_stats(const FileStats *s) {
    printf("Total lines:    %d\n", s->total_lines);
    printf("Blank lines:    %d\n", s->blank_lines);
    printf("Total chars:    %d\n", s->total_chars);
    printf("Alpha chars:    %d\n", s->alpha_chars);
    if (s->total_chars > 0) {
        printf("Alpha ratio:    %.1f%%\n",
               100.0 * s->alpha_chars / s->total_chars);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <file>\n", argv[0]);
        return 1;
    }
    FileStats stats;
    if (read_file_stats(argv[1], &stats) == 0) {
        print_stats(&stats);
    }
    return 0;
}

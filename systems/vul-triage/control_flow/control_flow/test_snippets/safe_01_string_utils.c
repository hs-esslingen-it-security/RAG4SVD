/*
 * safe_01_string_utils.c
 * 安全的字符串工具函数集合 —— 无漏洞
 * 所有拷贝均使用 strncpy + 显式 null 终止，长度由调用者传入。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#define MAX_NAME 64

/* 安全拷贝：保证 null 终止 */
void safe_copy(char *dst, size_t dst_sz, const char *src) {
    if (dst == NULL || src == NULL || dst_sz == 0)
        return;
    strncpy(dst, src, dst_sz - 1);
    dst[dst_sz - 1] = '\0';
}

/* 将字符串原地转为大写 */
void to_upper(char *s) {
    if (s == NULL) return;
    for (size_t i = 0; s[i] != '\0'; i++) {
        s[i] = (char)toupper((unsigned char)s[i]);
    }
}

/* 统计字符出现次数 */
int count_char(const char *s, char c) {
    int cnt = 0;
    if (s == NULL) return 0;
    for (size_t i = 0; s[i] != '\0'; i++) {
        if (s[i] == c) cnt++;
    }
    return cnt;
}

/* 连接两个字符串到堆缓冲区，调用者负责释放 */
char *safe_concat(const char *a, const char *b) {
    if (a == NULL || b == NULL) return NULL;
    size_t la = strlen(a);
    size_t lb = strlen(b);
    char *buf = (char *)malloc(la + lb + 1);
    if (buf == NULL) return NULL;
    memcpy(buf, a, la);
    memcpy(buf + la, b, lb);
    buf[la + lb] = '\0';
    return buf;
}

/* 反转字符串 */
void reverse_str(char *s) {
    if (s == NULL) return;
    size_t len = strlen(s);
    for (size_t i = 0; i < len / 2; i++) {
        char tmp = s[i];
        s[i] = s[len - 1 - i];
        s[len - 1 - i] = tmp;
    }
}

int main(void) {
    char name[MAX_NAME];
    safe_copy(name, sizeof(name), "hello world");
    to_upper(name);
    printf("Upper: %s\n", name);
    printf("Count 'L': %d\n", count_char(name, 'L'));

    char *joined = safe_concat(name, " !!!");
    if (joined) {
        reverse_str(joined);
        printf("Reversed concat: %s\n", joined);
        free(joined);
    }
    return 0;
}

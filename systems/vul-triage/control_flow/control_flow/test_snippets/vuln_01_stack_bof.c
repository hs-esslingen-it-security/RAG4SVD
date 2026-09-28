/*
 * vuln_01_stack_bof.c
 * 漏洞类型：栈缓冲区溢出 (Stack Buffer Overflow)
 * gets() 不检查长度，攻击者可覆盖返回地址。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define BUF_SIZE 32

typedef struct {
    char username[BUF_SIZE];
    int  privilege;
} UserInfo;

void init_user(UserInfo *u) {
    memset(u->username, 0, BUF_SIZE);
    u->privilege = 0;
}

void greet(const UserInfo *u) {
    if (u->privilege > 0) {
        printf("Welcome admin: %s\n", u->username);
    } else {
        printf("Hello user: %s\n", u->username);
    }
}

/* 漏洞：gets() 无边界检查，可溢出覆盖 privilege 字段 */
void read_username(UserInfo *u) {
    char tmp[BUF_SIZE];
    printf("Enter username: ");
    gets(tmp);                     /* VULN: unbounded read */
    strcpy(u->username, tmp);      /* VULN: no size check */
}

int check_admin(const char *name) {
    if (strcmp(name, "root") == 0) return 1;
    if (strcmp(name, "admin") == 0) return 1;
    return 0;
}

void process_login(UserInfo *u) {
    read_username(u);
    if (check_admin(u->username)) {
        u->privilege = 1;
    }
    greet(u);
}

int main(void) {
    UserInfo user;
    init_user(&user);
    process_login(&user);
    printf("Final privilege level: %d\n", user.privilege);
    return 0;
}

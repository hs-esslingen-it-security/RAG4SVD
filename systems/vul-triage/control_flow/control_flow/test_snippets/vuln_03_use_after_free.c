/*
 * vuln_03_use_after_free.c
 * 漏洞类型：Use-After-Free (UAF)
 * 对象被 free 后指针未置 NULL，后续继续读写已释放内存。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NAME_LEN 48

typedef struct Session {
    int  id;
    char name[NAME_LEN];
    int  is_active;
    void (*on_close)(struct Session *);
} Session;

void default_close(Session *s) {
    printf("Closing session %d (%s)\n", s->id, s->name);
    s->is_active = 0;
}

Session *session_create(int id, const char *name) {
    Session *s = (Session *)malloc(sizeof(Session));
    if (!s) return NULL;
    s->id = id;
    strncpy(s->name, name, NAME_LEN - 1);
    s->name[NAME_LEN - 1] = '\0';
    s->is_active = 1;
    s->on_close = default_close;
    return s;
}

void session_close(Session *s) {
    if (s && s->on_close) {
        s->on_close(s);
    }
}

/* 漏洞：free 后没有将指针置 NULL */
void session_destroy(Session *s) {
    free(s);
    /* 缺少: s = NULL; 或通知调用方 */
}

void print_session(const Session *s) {
    if (s == NULL) return;
    printf("Session[%d] name=%s active=%d\n", s->id, s->name, s->is_active);
}

int main(void) {
    Session *s1 = session_create(1, "alice");
    Session *s2 = session_create(2, "bob");

    print_session(s1);
    print_session(s2);

    session_close(s1);
    session_destroy(s1);

    /* VULN: s1 已被 free，但这里仍然使用它 */
    printf("Checking s1 after destroy:\n");
    print_session(s1);         /* UAF read */
    s1->is_active = 99;       /* UAF write */

    /* 再分配一块同样大小的内存，可能重用 s1 的块 */
    Session *s3 = session_create(3, "charlie");
    print_session(s3);

    /* 此时 s1 可能指向 s3 的内存 */
    printf("s1 after realloc: id=%d name=%s\n", s1->id, s1->name);

    session_destroy(s2);
    session_destroy(s3);
    return 0;
}

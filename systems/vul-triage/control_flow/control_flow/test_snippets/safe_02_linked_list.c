/*
 * safe_02_linked_list.c
 * 安全的单链表实现 —— 无漏洞
 * 所有节点均正确分配和释放，无悬挂指针。
 */
#include <stdio.h>
#include <stdlib.h>

typedef struct Node {
    int data;
    struct Node *next;
} Node;

Node *create_node(int val) {
    Node *n = (Node *)malloc(sizeof(Node));
    if (n == NULL) {
        fprintf(stderr, "malloc failed\n");
        return NULL;
    }
    n->data = val;
    n->next = NULL;
    return n;
}

void push_front(Node **head, int val) {
    Node *n = create_node(val);
    if (n == NULL) return;
    n->next = *head;
    *head = n;
}

int pop_front(Node **head) {
    if (*head == NULL) return -1;
    Node *tmp = *head;
    int val = tmp->data;
    *head = tmp->next;
    free(tmp);
    return val;
}

int list_length(const Node *head) {
    int cnt = 0;
    while (head != NULL) {
        cnt++;
        head = head->next;
    }
    return cnt;
}

void print_list(const Node *head) {
    printf("[");
    while (head != NULL) {
        printf("%d", head->data);
        if (head->next) printf(", ");
        head = head->next;
    }
    printf("]\n");
}

void free_list(Node **head) {
    Node *cur = *head;
    while (cur != NULL) {
        Node *next = cur->next;
        free(cur);
        cur = next;
    }
    *head = NULL;
}

int main(void) {
    Node *list = NULL;
    for (int i = 1; i <= 10; i++) {
        push_front(&list, i * 3);
    }
    printf("Length: %d\n", list_length(list));
    print_list(list);

    printf("Popped: %d\n", pop_front(&list));
    printf("Popped: %d\n", pop_front(&list));
    print_list(list);

    free_list(&list);
    printf("After free, length: %d\n", list_length(list));
    return 0;
}

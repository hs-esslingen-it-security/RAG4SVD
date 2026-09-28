/*
 * vuln_05_double_free.c
 * 漏洞类型：Double Free
 * 错误的引用计数和分支逻辑导致同一缓冲区被释放两次。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PAYLOAD_MAX 128

typedef struct Packet {
    int   type;
    int   length;
    char *payload;
    int   ref_count;
} Packet;

Packet *packet_create(int type, const char *data, int len) {
    Packet *p = (Packet *)malloc(sizeof(Packet));
    if (!p) return NULL;
    p->type = type;
    p->length = (len > PAYLOAD_MAX) ? PAYLOAD_MAX : len;
    p->payload = (char *)malloc(p->length + 1);
    if (!p->payload) {
        free(p);
        return NULL;
    }
    memcpy(p->payload, data, p->length);
    p->payload[p->length] = '\0';
    p->ref_count = 1;
    return p;
}

void packet_addref(Packet *p) {
    if (p) p->ref_count++;
}

/* 漏洞：ref_count 减到 0 时释放 payload，但不置 NULL */
void packet_release(Packet *p) {
    if (!p) return;
    p->ref_count--;
    if (p->ref_count <= 0) {
        free(p->payload);        /* 第一次释放 payload */
        /* 缺少: p->payload = NULL; */
        free(p);
    }
}

void packet_print(const Packet *p) {
    if (!p) return;
    printf("Packet[type=%d len=%d ref=%d]: %s\n",
           p->type, p->length, p->ref_count,
           p->payload ? p->payload : "(null)");
}

Packet *packet_clone(const Packet *src) {
    if (!src) return NULL;
    return packet_create(src->type, src->payload, src->length);
}

void process_packets(Packet *p1, Packet *p2) {
    packet_print(p1);
    packet_print(p2);

    /* 模拟业务逻辑：两条路径都可能释放 p1 */
    if (p1->type == p2->type) {
        printf("Same type, releasing p1 via path A\n");
        packet_release(p1);      /* 路径 A 释放 */
    }

    /* 漏洞：这里没有检查 p1 是否已被释放，再次释放 */
    printf("Cleanup: releasing p1 via path B\n");
    packet_release(p1);          /* VULN: double free if same type */
}

int main(void) {
    Packet *pkt1 = packet_create(1, "hello world", 11);
    Packet *pkt2 = packet_create(1, "test data", 9);

    if (!pkt1 || !pkt2) {
        fprintf(stderr, "Failed to create packets\n");
        return 1;
    }

    Packet *pkt3 = packet_clone(pkt1);
    packet_print(pkt3);

    /* 触发漏洞：pkt1 和 pkt2 类型相同 */
    process_packets(pkt1, pkt2);

    packet_release(pkt2);
    packet_release(pkt3);
    return 0;
}

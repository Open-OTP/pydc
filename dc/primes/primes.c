#include <stdlib.h>
#include <math.h>
#include <string.h>



typedef unsigned int prime_t;


enum { WORD_SIZE = sizeof(prime_t) * 8 };

static prime_t* PRIMES = NULL;


prime_t* make_bitarray(prime_t num_bits){
  int num_bytes = (sizeof(prime_t) - 1 + num_bits)/sizeof(prime_t);
  prime_t* bitarray = (prime_t *)malloc(num_bytes);
  memset(bitarray, 0xFF, num_bytes);
  return bitarray;
}



static inline int bindex(int b) { return b / WORD_SIZE; }
static inline int boffset(int b) { return b % WORD_SIZE; }



static inline void set_bit(prime_t * bitarray, int b) {
    bitarray[bindex(b)] |= 1 << (boffset(b));
}

static inline void clear_bit(prime_t * bitarray, int b) {
    bitarray[bindex(b)] &= ~(1 << (boffset(b)));
}

static inline prime_t get_bit(prime_t* bitarray, int b) {
    return bitarray[bindex(b)] & (1 << (boffset(b)));
}


void free_primes(){
  if (PRIMES == NULL)
    return;
  free(PRIMES);
  PRIMES = NULL;
}


int initialize_primes(prime_t n){
  if(PRIMES != NULL)
    free_primes();

  int sieve_size = n / 3 + (n % 6 == 2);
  prime_t* sieve = make_bitarray(sieve_size);
  const int bi = ((int)pow(n, 0.5)) / 3 + 1;


  for(int i = 1; i < bi; i++){
      if(get_bit(sieve, i)){
          int x;
          int y;
          int k = (3 * i + 1) | 1;

          x = k * k / 3;
          y = 2 * k;
          for(;x < sieve_size; x+= y)
            clear_bit(sieve, x);

          x = k * (k - 2 * (i & 1) + 4) / 3;
          for(;x < sieve_size; x+= y)
            clear_bit(sieve, x);
      }
  }

  int prime_count = 2;
  for(int i = 1; i < sieve_size; i++){
     if(get_bit(sieve, i)){
        prime_count += 1;
     }
  }

  PRIMES = malloc(prime_count * sizeof(prime_t));
  PRIMES[0] = 2;
  PRIMES[1] = 3;
  int pi = 2;

  for(int i = 1; i < sieve_size; i++){
     if(get_bit(sieve, i)){
        PRIMES[pi] = (3 * i + 1) | 1;
        pi++;
     }
  }

  free(sieve);

  return prime_count;
};


extern inline prime_t get_prime(int i){
    if (PRIMES == NULL)
        return 0;
    return PRIMES[i];
};

int primes_defined(){
    return PRIMES != NULL;
}
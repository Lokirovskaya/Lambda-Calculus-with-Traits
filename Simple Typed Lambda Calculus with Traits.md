## Simple Typed Lambda Calculus with Traits

Basic Types 

* Int
* Bool
* String
* List

```rust
trait Summary a {
    summarize : a -> String;
}
    
struct NewsAritcle{
    headline : String;
    location : String;
}

impl Summary for NewsAritcle{
    summarize = printf "{}-{}" headline location;
}
```

\// commentS
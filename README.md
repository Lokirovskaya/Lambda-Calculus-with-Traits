# Traits in Lambda Calculus

2025 DPPL Project

[TOC]

## 1. 简介与运行

基于 System F 的扩展，通过 record 传递的方式实现了 trait.



本语言实现了以下的核心特性

* 基于 System F，实现 parametric polymorphism
* 支持 trait，实现 ad-hoc polymorphism
* 支持手写带 trait 约束的 type param (constrained type) ★
* 支持简单的类型推断 ★
* 支持 record 数据类型
* 支持 list 数据类型 ★

其中，标 ★ 的是在计划外额外实现的功能



**如何运行项目**

```shell
python main.py <filename> [--debug]
```

项目运行在 Python 3.12，不依赖其它包。



已有测试用例在 test 文件夹下，分别为

* basic.rs - 测试语言基本功能
* lambda.rs - 测试 System F
* trait.rs - 测试 trait 实现

运行后，当前目录下生成一系列中间步骤输出文件，分别为

* step1_desugar.rs - 拆解 trait, struct, impl 语句后的结果
* step2_type_solved.rs - 化简类型定义语句后的结果
* step3_type_checked.rs - 进行类型推导和类型检查后的结果。在每条语句后标注语句的类型，同时补齐推导出的类型参数
* step4_dispatched.rs - 静态分发 trait 实例后的结果
* step5_eval.rs - 解释执行后的结果。在每条语句后标注语句的执行输出





## 2. 语言设计

### 2.1 基础功能

基本单位是语句，不同语句之间使用分号分隔。

语言基本类型有 `Int`, `String`, `Bool`，支持 `+-*/%` 算数运算，`&&`, `||`, `!` 布尔运算，以及 `>`, `>=`, `==`, `!=` 等比较运算。

```rust
1 + 1;         // 2
x = 3;         // 3
y = 5;         // 5
x == (y - 2);  // true
```

Lambda 表达式 `\x:Type. Body`

```rust
add1 = \x:Int. x+1;  // add1: Int -> Int
add1 2;              // 3
```

类型抽象 `\T. Body`

类型应用 `f @T`，通常可以省略，由参数类型推断

```rust
id = \T. \x:T. x;   // id: forall T. T -> T.
id @Int 4;          // 4
id id;              // id
id false;           // false
```

此外，可使用 `print`, `println`, `read` 函数从控制台读取输入或进行输出



### 2.2 Traits & Struct

Trait 声明。其中 `a` 为类型参数

```rust
trait Show a {
    show: a -> String;
}
```

Struct 声明

```rust
struct People {
    name: String;
    age: Int;
}
```

Trait implementation, 得到 ad-hoc polymorphism 的函数 show

```rust
impl Show for Int {
    show = int_to_string;
}
impl Show for String {
    show = \x:String. x;
}
impl Show for People {
    show = \p:People. "Name: " + p.name + ", Age: " + (int_to_string p.age);
}
```

由于有类型推断，可直接使用 show

```rust
show 1;                   // "1"
show "A";                 // "A"
show (People "Xyy" 22);   // "Name: Xyy, Age: 22"
```



### 2.3 Constrained Type Param

类型抽象时，类型参数可以指定 impl 的 trait，从而使得多态类型也能够被 trait 函数调用。

```rust
show_twice = \T impl Show. \x: T. (show x) + (show x);
show_twice 1;                    // "11"
show_twice "A";                  // "AA"
show_twice (People "Xyy" 22);    // "Name: Xyy, Age: 22Name: Xyy, Age: 22"
```

这里如果不指定 `T impl Show`，会产生错误

```
Type Error: Type 'T' does not satisfy trait bounds 'Show' required by 'show'
```

可以同时对一个类型指定多个 trait constraints，用加号 `+` 分隔，见更多示例 3.1。



### 2.4 错误检查

表达式类型检查

```rust
1 + "Int"
// Type Error: Expected 'Int', got 'String'
```

非法调用检查

```rust
(\x: Bool. !x) "Ohh?";
// Type Error: Expected 'Bool', got 'String'
```

Exhaustiveness 检查：Trait 实例化时必须不增加、不遗漏每一个函数。（由于是 recode type 代为检查，报错不特别清晰）

```rust
trait Container a {
    len: a -> Int;
    first: a -> a;
}

impl Container for [Int] {
    first = \l:[Int]. [head l];
}

// [Line 6] Type Error: Annotated type '{len: [Int] -> Int, first: [Int] -> [Int]}', got '{first: [Int] -> [Int]}'
```

约束检查：trait 函数是否应用到了没有实现的类型？

```rust
trait Show a {
    show: a -> String;
}

impl Show for Int {
    show = int_to_string;
}

show true;

// [Line 7] Type Error: Type 'Bool' does not satisfy trait bounds 'Show' required by 'show'
```







## 3. 更多示例

### 3.1 多重 traits 约束

实现了 show_if_equal 函数，它需要传入的类型参数既能够 show 又能够使用 eq 比较

```rust 
trait Show a {
    show: a -> String;
}
trait Eq a {
    eq: a -> a -> Bool;
}

struct Point {
    x: Int;
    y: Int;
}

impl Show for Point {
    show = \p:Point. "(" + (int_to_string p.x) + ", " + (int_to_string p.y) + ")";
}
impl Eq for Point {
    eq = \p1:Point. \p2:Point. p1.x == p2.x && p1.y == p2.y;
}

show_if_equal = \T impl Show + Eq.   // [[[Multiple trait bounds here]]]
    \a:T. \b:T.
        if (eq a b) then (show a) else "Not equal";

show_if_equal (Point 1 2) (Point 1 2);   // "(1, 2)"
show_if_equal (Point 1 2) (Point 3 4);   // "Not equal"
```

### 3.2 打印一个矩阵

终端上会打印一个 3*3 矩阵

```rust
elem_0 = \T. \xs: [T]. head xs;
elem_1 = \T. \xs: [T]. head (tail xs);
elem_2 = \T. \xs: [T]. head (tail (tail xs));

trait Show a {
    show: a -> String;
}
impl Show for Int {
    show = int_to_string;
}
impl Show for [Int] {
    show = \xs:[Int]. 
        show (elem_0 xs) + " " + show (elem_1 xs) + " " + show(elem_2 xs);
}
impl Show for [[Int]] {
    show = \xs:[[Int]]. 
        show (elem_0 xs) + "\n" + show (elem_1 xs) + "\n" + show(elem_2 xs);
}
print (show [[1, 2, 3], [4, 5, 6], [7, 8, 9]]);
```







## 4. 形式化

### 4.1 List Type

List 的文法为 `[term, ...]`，类型为 `[T]`，支持 `cons`, `head`, `tail` 操作

**Evaluation Rules**

内部元素的 evaluate 顺序是从左到右 
$$
\mathtt{
\frac{t_1\to t_1'}{[t_1,\cdots]\to [t_1',\cdots]} \tag{E-List1}
}
$$

$$
\mathtt{
\frac{t_k\to t_k'}{[v_1,\cdots,v_{k-1},t_k,\cdots]\to [v_1,\cdots,v_{k-1},t_k',\cdots]} \tag{E-List2}
}
$$

函数 cons 用于将一个元素放到开头
$$
\mathtt{
cons\ @T\ v_1\ []\to [v_1] \tag{E-ConsEmpty}
}
$$

$$
\mathtt{
cons\ @T\ v_1\ [v_2,\cdots]\to [v_1,v_2,\cdots] \tag{E-Cons}
}
$$

函数 head 提取第一个元素，对于空列表触发 run-time error
$$
\mathtt{
head\ @T\ []\to Error \tag{E-HeadEmpty}
}
$$

$$
\mathtt{
head\ @T\ [v_1, v_2,\cdots]\to v_1 \tag{E-Head}
}
$$

函数 tail 提取除第一个元素外的其余元素
$$
\mathtt{
tail\ @T\ []\to [] \tag{E-TailEmpty}
}
$$

$$
\mathtt{
tail\ @T\ [v_1, v_2,\cdots]\to [v_2, \cdots] \tag{E-Tail}
}
$$

**Typing Rules**

空 list 的类型是多态的
$$
\mathtt{
\Gamma\vdash []:\forall a.[a] \tag{T-ListEmpty}
}
$$
List 元素的类型应当一致
$$
\mathtt{
\frac{\mathrm{for\ each\ \it i}\quad\Gamma\vdash t_i:T}{\Gamma\vdash[t_1,t_2,\cdots]:[T]} \tag{T-ListEmpty}
}
$$
对于 cons 应用空列表的情况，会得到实例化的列表
$$
\mathtt{
\frac{\Gamma\vdash t_1:T}{\Gamma\vdash cons\ @T\ t_1\ []:[T] } \tag{T-ConsEmpty}
}
$$
列表非空的情况略

函数 head 和 tail 类似。他们分别有类型 `[T] -> T` 和 `[T] -> [T]`



### 4.2 Struct

Struct 是 record 的语法糖，这里只展示翻译到 record 的过程，略过 evaluation rules 和 typing rules.

翻译函数 `σ(src | ctx) = target`.

对于每个 `struct` 语句，使用一个 context $\Delta$ 来存储 struct 的字段类型映射
$$
\mathtt{
\frac{l_1:T_1,l_2:T_2, \cdots \in\Delta[S]}{\Delta[S]\vdash struct\ S\  \{l_1:T_1,l_2:T_2, \cdots \} }
}
$$
对于 Struct `S` 的构造函数 `S`，翻译成构造 record
$$
\mathtt{
\sigma_{term}(S\ |\ \Delta[S]) = \lambda a_1:T_1.\lambda a_2:T_2.\cdots.\{l_1=a_1, l_2=a_2, \cdots\}
}\tag{4.2.1}
$$
同时 `S` 也是一个 type（与构造函数通过上下文区分）
$$
\mathtt{
\sigma_{type}(S\ |\ \Delta[S]) = \{l_1:T_1,l_2:T_2, \cdots \}
}\tag{4.2.2}
$$



### 4.3 Traits

同上节，只形式化翻译到 System F 的过程。

对于每个 `trait` 语句，使用一个 context $\Delta$ 记录 trait 函数的类型
$$
\mathrm{for\ each\ \it i}\quad\mathtt{
\frac{f_i:\forall a.T_i\in\Delta[F]}{\Delta[F]\vdash trait\ F\ a\  \{f_i:T_i\} }
}
$$
并将其加入到类型检查的上下文中，用于 System F 的类型检查
$$
\mathrm{for\ each\ trait\ F_i}\quad\mathtt{
\frac{f_i:T_i\in\Delta[F_i]}{f_i:T_i\in\Gamma}
}
$$
同时 `F` 也是一个 type
$$
\mathtt{
\sigma_{type}(F\ |\ \Delta[F]) = \forall a. \{l_1:T_1,l_2:T_2, \cdots \}
}\tag{4.3.1}
$$


对于每个 `impl` 语句，使用一个 context $\Sigma$ 记录 trait 对应的 record 实例
$$
\mathrm{for\ each\ \it i}\quad\mathtt{
\frac{\{f_i=x_i\}\in\Sigma[F,S]}{\Sigma[F,S]\vdash impl\ F\ for\  S\  \{f_i=x_i\} }
}
$$
在此时，会检查 $\mathtt{\{f_i=x_i\}}$ 的类型是否为 $\mathtt{F\ \ S}$，相当于：

* Exhaustiveness checking：如果 impl 块中含有缺少/增多/不匹配的函数，会被 record type checking 检查出 label 不匹配；
* 类型一致性检查：如果 impl 块中的实现的类型与声明的类型不符，也会被 record type checking 检查。

对于每一个 trait 函数调用，根据后续接的类型实参，查找对应的 record 实例
$$
\mathtt{
\sigma_{term}(f\ @S\ |\ \Delta[F],\Sigma[F,S]) = dict\_F\_S.f\ \ @S
}\tag{4.3.2}
$$
例如

```rust
trait Show a {show: a -> String;}
impl Show for Int {show = int_to_string;}
impl Show for String {show = id;}
show @Int 1
```

那么有翻译如下
$$
\mathtt{\Delta[Show]=show: \forall a. a\to String}\\
\mathtt{Show:\forall a. \{show: a\to String\}}\\
\mathtt{\Sigma[Show, Int]= \{show = int\_to\_string\}}\\
\mathtt{\Sigma[Show, String]= \{show = id\}} \\
\mathtt{\sigma(show\ @Int\ 1\ |\ \Delta[Show], \Sigma[Show,Int]) = \{show = int\_to\_string\}.show\ \ 1}
$$



### 4.4 Constrained Type Param

对于手动标记 trait 约束，例如 `\T impl Show+Add` 的类型抽象，将每个约束扩充为一个 record 形参
$$
\mathtt{
\sigma_{term}(\Lambda a\ impl\ F_1+F_2+\cdots. t\ |\ \Delta) = \Lambda a.\lambda r_1:(F_1\ a).\lambda r_2:(F_2\ a). \sigma_{term}(t\ |\ \Delta)
}\tag{4.4.1}
$$

并在调用处传入 record 实参
$$
\mathtt{\frac{\Gamma\vdash f:\forall a\ impl\ F_1+F_2+\cdots\qquad \Sigma[F_1,S]=r_1\qquad\Sigma[F_2,S]=r_2\qquad\cdots}{\sigma_term(f\ @S\ t\ |\ \Sigma)=f\ \ @S\ \ r_1\ \  r_2\ \ \sigma_{term}(t\ |\ \Sigma)}}\tag{4.4.2}
$$



### 4.5 类型推断

使用了简易版的 unification 算法。

对于只有一个未知变量的类型表达式，尝试和某个目标类型表达式 unify，解出未知量.

假设未知类型是 $\mathtt X$，已知类型是 $\mathtt {A}$. 符号 $\and$ 表示比较两边结果，若相同则返回，若不同则 unify 失败
$$
\begin{align}
\mathtt{unify(X, A)}&=\mathtt{A}\\
\mathtt{unify(X_l\to X_r, A_l\to A_r)}&=\mathtt{unify(X_l, A_l)\and unify(X_r, A_r)}\\
\mathtt{unify([X], [A])}&=\mathtt{unify(X, A)}\\
\mathtt{unify(\{l_i:X_i\}, \{l_i:A_i\})}&=\mathtt{{\large \and_i}\ unify(X_i, A_i)}\\
\mathtt{otherwise}&=\mathtt{fail}
\end{align}
$$
对于所有形如 $\mathtt{(\Lambda X. \lambda x:T. t_1)\ t_2}$ 的语句，做以下变换
$$
\mathtt{\frac{\Gamma\vdash t_2:T_2\qquad unify(X,T_2)=U}{\sigma_{term}(\mathtt{(\Lambda X. \lambda x:T_0. t_1)\ t_2}) = \mathtt{(\Lambda X. \lambda x:T_0. \sigma_{term}(t_1))\ @U\ \ \sigma_{term}(t_2)}}}\tag{4.5.1}
$$






## 5. Soundness 证明

主要证明 trait 部分。

由于 System F 的 soundness 是已证明的，故只需说明：使用前文的转换方式得到的 term 都对应一个 evaluation rule 或者是 value，且它们是 well-typed 的.

由于转换得到的 term 大多是 lambda 或 record，

* 对于转换 (4.2.1)，观察可知这是一个 value。式中 $\mathtt{T_1, T_2,\cdots}$ 都是经类型检查的 types，按照此式的构造方式，有类型 

$$
\mathtt{T_1\to T_2\to\cdots\to \{l_1:T_1,l_2:T_2, \cdots \}}
$$

​	所以它是 well-typed 的。

* 对于转换 (4.2.2)，是对 type 的翻译，不涉及 term.
* 对于转换 (4.3.1)，是对 type 的翻译，不涉及 term.
* 对于转换 (4.3.2)
  * $\mathtt{dict\_F\_S.f}$ 一定可以继续 eval，因为 $\mathtt{dict\_F\_S}$ 是来自于 $\mathtt{\Sigma[F,S]}$（查找 trait F 关于类型 S 的实例得到的 record），由 exhaustiveness checking（参考上文，所有的 trait 字段都需要被实例化）保证这一 record 中一定含有 label `f`. 此外，由于它是 forall type，后面的 `@S` 也能让他使用 TypeApp 规则继续 eval.
  * 由于 trait 必须要一个类型参数，$\mathtt{dict\_F\_S.f}$ 的类型有 $\mathtt{\forall a.T}$ 的形式，因此原式有类型 $\mathtt{T[a\mapsto S]}$.
* 对于转换 (4.4.1)
  * 只是添加了几个 lambda 参数，不会影响是否可以继续 eval
  * 由于 trait 必须要一个类型参数，trait 类型 $\mathtt{F_i}$ 有 $\mathtt{\forall x.T}$ 的形式，因此 $\mathtt{F_i\ a:T_i[x\mapsto a]}$，原式有类型

$$
\mathtt{\forall a.T_2[x\to a]\to T_2[x\to a]\to\cdots\to\Gamma(\sigma_{term}(t))}
$$

* 对于转换 (4.4.2)
  * 显然可以继续 eval，只需证明是 well-typed
  * 由 (4.4.1) 的变换，带约束的函数 `f` 在定义位置根据约束的数量添上了 record 形参，而此变换表示在使用位置同样添加相同类型的 record 实参，因此两者相抵消，变换前后的类型不发生改变。
* 对于转换 (4.5.1)
  * 正确性由 unification 算法保证。


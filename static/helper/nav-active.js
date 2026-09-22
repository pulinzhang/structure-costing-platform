(() => {
  const toc = document.querySelector(".page-toc");
  if (!toc) return;

  const links = [...toc.querySelectorAll('a[href^="#"]')];
  if (!links.length) return;

  const setActive = (id) => {
    links.forEach((link) => {
      link.classList.toggle("is-active", link.hash === `#${id}`);
    });
  };

  const fromHash = () => {
    const id = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (id && document.getElementById(id)) setActive(id);
  };

  links.forEach((link) => {
    link.addEventListener("click", () => {
      const id = link.hash.slice(1);
      if (id) setActive(id);
    });
  });

  window.addEventListener("hashchange", fromHash);

  const sections = links
    .map((link) => document.getElementById(link.hash.slice(1)))
    .filter(Boolean);
  if (typeof IntersectionObserver === "function" && sections.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio);
        if (visible[0] && visible[0].target.id) setActive(visible[0].target.id);
      },
      { rootMargin: "-18% 0px -68% 0px", threshold: [0, 0.25, 0.5, 1] },
    );
    sections.forEach((section) => observer.observe(section));
  }

  fromHash();
})();

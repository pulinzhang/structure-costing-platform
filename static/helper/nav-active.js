(() => {
  const toc = document.querySelector(".page-toc");
  if (!toc) return;

  const links = [...toc.querySelectorAll('a[href^="#"]')];
  if (!links.length) return;

  let pinnedId = "";
  let settleTimer = 0;

  const setActive = (id) => {
    links.forEach((link) => {
      link.classList.toggle("is-active", link.hash === `#${id}`);
    });
  };

  const sectionIdFromHash = (hash) => decodeURIComponent(hash.replace(/^#/, ""));

  const releasePin = () => {
    const id = pinnedId;
    if (!id) return;
    setActive(id);
    window.setTimeout(() => {
      if (pinnedId === id) pinnedId = "";
    }, 80);
  };

  const pin = (id) => {
    if (!id || !document.getElementById(id)) return;
    pinnedId = id;
    setActive(id);
    window.clearTimeout(settleTimer);
    settleTimer = window.setTimeout(releasePin, 140);
  };

  links.forEach((link) => {
    link.addEventListener("click", () => {
      pin(sectionIdFromHash(link.hash));
    });
  });

  window.addEventListener("hashchange", () => {
    pin(sectionIdFromHash(location.hash));
  });

  window.addEventListener(
    "scroll",
    () => {
      if (!pinnedId) return;
      window.clearTimeout(settleTimer);
      settleTimer = window.setTimeout(releasePin, 140);
    },
    { passive: true },
  );

  const sections = links
    .map((link) => document.getElementById(sectionIdFromHash(link.hash)))
    .filter(Boolean);
  if (typeof IntersectionObserver === "function" && sections.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        if (pinnedId) return;
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio);
        if (visible[0] && visible[0].target.id) setActive(visible[0].target.id);
      },
      { rootMargin: "-18% 0px -68% 0px", threshold: [0, 0.25, 0.5, 1] },
    );
    sections.forEach((section) => observer.observe(section));
  }

  const initialId = sectionIdFromHash(location.hash);
  if (initialId && document.getElementById(initialId)) setActive(initialId);
})();
